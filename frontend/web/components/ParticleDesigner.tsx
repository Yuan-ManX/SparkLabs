import React, { useState, useCallback, useEffect, useRef } from 'react';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
  startSize: number;
  endSize: number;
  colorStart: string;
  colorEnd: string;
  alphaStart: number;
  alphaEnd: number;
}

interface ParticlePreset {
  name: string;
  emissionRate: number;
  maxParticles: number;
  emitterShape: string;
  shapeRadius: number;
  shapeWidth: number;
  shapeHeight: number;
  shapeAngle: number;
  textureType: string;
  startSize: number;
  endSize: number;
  startColor: string;
  endColor: string;
  startOpacity: number;
  endOpacity: number;
  blendMode: string;
  speedMin: number;
  speedMax: number;
  direction: number;
  spreadAngle: number;
  gravityX: number;
  gravityY: number;
  radialAccel: number;
  tangentialAccel: number;
  damping: number;
  lifetimeMin: number;
  lifetimeMax: number;
  burstCount: number;
  preWarm: boolean;
  localSpace: boolean;
  sortingMode: string;
}

const PRESETS: Record<string, ParticlePreset> = {
  Fire: {
    name: 'Fire',
    emissionRate: 80,
    maxParticles: 300,
    emitterShape: 'circle',
    shapeRadius: 30,
    shapeWidth: 60,
    shapeHeight: 20,
    shapeAngle: 0,
    textureType: 'circle',
    startSize: 12,
    endSize: 4,
    startColor: '#ff6600',
    endColor: '#ff0000',
    startOpacity: 1,
    endOpacity: 0,
    blendMode: 'additive',
    speedMin: 40,
    speedMax: 120,
    direction: -90,
    spreadAngle: 30,
    gravityX: 0,
    gravityY: 30,
    radialAccel: 0,
    tangentialAccel: 0,
    damping: 0.96,
    lifetimeMin: 0.4,
    lifetimeMax: 1.2,
    burstCount: 0,
    preWarm: false,
    localSpace: false,
    sortingMode: 'none',
  },
  Sparkle: {
    name: 'Sparkle',
    emissionRate: 30,
    maxParticles: 150,
    emitterShape: 'point',
    shapeRadius: 10,
    shapeWidth: 40,
    shapeHeight: 40,
    shapeAngle: 0,
    textureType: 'star',
    startSize: 6,
    endSize: 2,
    startColor: '#ffdd44',
    endColor: '#ffaa00',
    startOpacity: 1,
    endOpacity: 0,
    blendMode: 'additive',
    speedMin: 50,
    speedMax: 150,
    direction: 0,
    spreadAngle: 360,
    gravityX: 0,
    gravityY: -10,
    radialAccel: -20,
    tangentialAccel: 0,
    damping: 0.98,
    lifetimeMin: 0.3,
    lifetimeMax: 0.8,
    burstCount: 20,
    preWarm: false,
    localSpace: false,
    sortingMode: 'none',
  },
  Smoke: {
    name: 'Smoke',
    emissionRate: 20,
    maxParticles: 120,
    emitterShape: 'circle',
    shapeRadius: 20,
    shapeWidth: 40,
    shapeHeight: 20,
    shapeAngle: 0,
    textureType: 'circle',
    startSize: 10,
    endSize: 40,
    startColor: '#888888',
    endColor: '#cccccc',
    startOpacity: 0.7,
    endOpacity: 0,
    blendMode: 'normal',
    speedMin: 15,
    speedMax: 40,
    direction: -90,
    spreadAngle: 20,
    gravityX: 0,
    gravityY: -5,
    radialAccel: 5,
    tangentialAccel: 0,
    damping: 0.99,
    lifetimeMin: 1.0,
    lifetimeMax: 3.0,
    burstCount: 0,
    preWarm: false,
    localSpace: false,
    sortingMode: 'none',
  },
  Rain: {
    name: 'Rain',
    emissionRate: 200,
    maxParticles: 500,
    emitterShape: 'rect',
    shapeRadius: 10,
    shapeWidth: 400,
    shapeHeight: 10,
    shapeAngle: 0,
    textureType: 'square',
    startSize: 4,
    endSize: 3,
    startColor: '#6699cc',
    endColor: '#6699cc',
    startOpacity: 0.8,
    endOpacity: 0.5,
    blendMode: 'normal',
    speedMin: 300,
    speedMax: 500,
    direction: 90,
    spreadAngle: 5,
    gravityX: 0,
    gravityY: 200,
    radialAccel: 0,
    tangentialAccel: 0,
    damping: 1,
    lifetimeMin: 0.5,
    lifetimeMax: 1.0,
    burstCount: 0,
    preWarm: false,
    localSpace: false,
    sortingMode: 'none',
  },
};

const EMITTER_SHAPES = ['point', 'line', 'circle', 'rect', 'cone', 'ring'];
const TEXTURE_TYPES = ['circle', 'square', 'star', 'sparkle', 'custom'];
const BLEND_MODES = ['normal', 'additive', 'multiply'];
const SORTING_MODES = ['none', 'distance', 'youngest', 'oldest'];

const THEME = {
  bg: '#1e1e2e',
  card: '#2a2a3e',
  accent: '#6c5ce7',
  text: '#e0e0e0',
  textDim: '#888888',
  border: '#3a3a5e',
  inputBg: '#1a1a2e',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    color: THEME.text,
    fontFamily: 'monospace',
    background: THEME.bg,
    overflow: 'hidden',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 16px',
    background: THEME.card,
    borderBottom: `1px solid ${THEME.border}`,
    flexShrink: 0,
    flexWrap: 'wrap',
  },
  toolbarInput: {
    background: THEME.inputBg,
    border: `1px solid ${THEME.border}`,
    color: THEME.text,
    padding: '6px 10px',
    borderRadius: 4,
    fontSize: 13,
    fontFamily: 'monospace',
    outline: 'none',
    minWidth: 140,
  },
  toolbarBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '6px 12px',
    borderRadius: 4,
    border: `1px solid ${THEME.border}`,
    background: THEME.inputBg,
    color: THEME.text,
    cursor: 'pointer',
    fontSize: 12,
    fontFamily: 'monospace',
    whiteSpace: 'nowrap',
  },
  toolbarBtnPrimary: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '6px 12px',
    borderRadius: 4,
    border: 'none',
    background: THEME.accent,
    color: '#ffffff',
    cursor: 'pointer',
    fontSize: 12,
    fontFamily: 'monospace',
    whiteSpace: 'nowrap',
  },
  body: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  leftPanel: {
    width: '40%',
    minWidth: 300,
    overflow: 'auto',
    padding: 12,
    borderRight: `1px solid ${THEME.border}`,
    background: THEME.bg,
  },
  rightPanel: {
    flex: 1,
    position: 'relative',
    background: '#14141e',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  section: {
    background: THEME.card,
    borderRadius: 6,
    marginBottom: 8,
    overflow: 'hidden',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    cursor: 'pointer',
    userSelect: 'none',
    fontSize: 13,
    fontWeight: 'bold',
    color: THEME.accent,
  },
  sectionBody: {
    padding: '8px 12px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  label: {
    fontSize: 11,
    color: THEME.textDim,
    minWidth: 90,
    flexShrink: 0,
  },
  input: {
    flex: 1,
    background: THEME.inputBg,
    border: `1px solid ${THEME.border}`,
    color: THEME.text,
    padding: '4px 8px',
    borderRadius: 3,
    fontSize: 12,
    fontFamily: 'monospace',
    outline: 'none',
  },
  select: {
    flex: 1,
    background: THEME.inputBg,
    border: `1px solid ${THEME.border}`,
    color: THEME.text,
    padding: '4px 6px',
    borderRadius: 3,
    fontSize: 12,
    fontFamily: 'monospace',
    outline: 'none',
    cursor: 'pointer',
  },
  colorInput: {
    width: 36,
    height: 28,
    border: `1px solid ${THEME.border}`,
    borderRadius: 3,
    cursor: 'pointer',
    background: THEME.inputBg,
    padding: 2,
  },
  presetBtn: {
    padding: '4px 10px',
    borderRadius: 3,
    border: `1px solid ${THEME.accent}`,
    background: 'transparent',
    color: THEME.accent,
    cursor: 'pointer',
    fontSize: 11,
    fontFamily: 'monospace',
  },
  presetBtnActive: {
    padding: '4px 10px',
    borderRadius: 3,
    border: `1px solid ${THEME.accent}`,
    background: THEME.accent,
    color: '#ffffff',
    cursor: 'pointer',
    fontSize: 11,
    fontFamily: 'monospace',
  },
  canvasOverlay: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    fontSize: 10,
    color: THEME.textDim,
  },
  emptyPreview: {
    color: THEME.textDim,
    fontSize: 14,
  },
  spacer: {
    flex: 1,
  },
};

const hexToRgb = (hex: string): [number, number, number] => {
  const h = hex.replace('#', '');
  return [
    parseInt(h.substring(0, 2), 16),
    parseInt(h.substring(2, 4), 16),
    parseInt(h.substring(4, 6), 16),
  ];
};

const lerpColor = (c1: string, c2: string, t: number): string => {
  const [r1, g1, b1] = hexToRgb(c1);
  const [r2, g2, b2] = hexToRgb(c2);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r},${g},${b})`;
};

const ParticleDesigner: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animFrameRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);
  const accumulatedRef = useRef<number>(0);

  const [effectName, setEffectName] = useState('Fire');
  const [isPlaying, setIsPlaying] = useState(true);
  const [activePreset, setActivePreset] = useState('Fire');

  const [emissionRate, setEmissionRate] = useState(80);
  const [maxParticles, setMaxParticles] = useState(300);
  const [emitterShape, setEmitterShape] = useState('circle');
  const [shapeRadius, setShapeRadius] = useState(30);
  const [shapeWidth, setShapeWidth] = useState(60);
  const [shapeHeight, setShapeHeight] = useState(20);
  const [shapeAngle, setShapeAngle] = useState(0);

  const [textureType, setTextureType] = useState('circle');
  const [startSize, setStartSize] = useState(12);
  const [endSize, setEndSize] = useState(4);
  const [startColor, setStartColor] = useState('#ff6600');
  const [endColor, setEndColor] = useState('#ff0000');
  const [startOpacity, setStartOpacity] = useState(1);
  const [endOpacity, setEndOpacity] = useState(0);
  const [blendMode, setBlendMode] = useState('additive');

  const [speedMin, setSpeedMin] = useState(40);
  const [speedMax, setSpeedMax] = useState(120);
  const [direction, setDirection] = useState(-90);
  const [spreadAngle, setSpreadAngle] = useState(30);
  const [gravityX, setGravityX] = useState(0);
  const [gravityY, setGravityY] = useState(30);
  const [radialAccel, setRadialAccel] = useState(0);
  const [tangentialAccel, setTangentialAccel] = useState(0);
  const [damping, setDamping] = useState(0.96);

  const [lifetimeMin, setLifetimeMin] = useState(0.4);
  const [lifetimeMax, setLifetimeMax] = useState(1.2);

  const [burstCount, setBurstCount] = useState(0);
  const [preWarm, setPreWarm] = useState(false);
  const [localSpace, setLocalSpace] = useState(false);
  const [sortingMode, setSortingMode] = useState('none');

  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});

  const toggleSection = useCallback((section: string) => {
    setCollapsedSections(prev => ({ ...prev, [section]: !prev[section] }));
  }, []);

  const applyPreset = useCallback((key: string) => {
    const preset = PRESETS[key];
    if (!preset) return;
    setActivePreset(key);
    setEffectName(preset.name);
    setEmissionRate(preset.emissionRate);
    setMaxParticles(preset.maxParticles);
    setEmitterShape(preset.emitterShape);
    setShapeRadius(preset.shapeRadius);
    setShapeWidth(preset.shapeWidth);
    setShapeHeight(preset.shapeHeight);
    setShapeAngle(preset.shapeAngle);
    setTextureType(preset.textureType);
    setStartSize(preset.startSize);
    setEndSize(preset.endSize);
    setStartColor(preset.startColor);
    setEndColor(preset.endColor);
    setStartOpacity(preset.startOpacity);
    setEndOpacity(preset.endOpacity);
    setBlendMode(preset.blendMode);
    setSpeedMin(preset.speedMin);
    setSpeedMax(preset.speedMax);
    setDirection(preset.direction);
    setSpreadAngle(preset.spreadAngle);
    setGravityX(preset.gravityX);
    setGravityY(preset.gravityY);
    setRadialAccel(preset.radialAccel);
    setTangentialAccel(preset.tangentialAccel);
    setDamping(preset.damping);
    setLifetimeMin(preset.lifetimeMin);
    setLifetimeMax(preset.lifetimeMax);
    setBurstCount(preset.burstCount);
    setPreWarm(preset.preWarm);
    setLocalSpace(preset.localSpace);
    setSortingMode(preset.sortingMode);
  }, []);

  const getCurrentConfig = useCallback((): ParticlePreset => ({
    name: effectName,
    emissionRate,
    maxParticles,
    emitterShape,
    shapeRadius,
    shapeWidth,
    shapeHeight,
    shapeAngle,
    textureType,
    startSize,
    endSize,
    startColor,
    endColor,
    startOpacity,
    endOpacity,
    blendMode,
    speedMin,
    speedMax,
    direction,
    spreadAngle,
    gravityX,
    gravityY,
    radialAccel,
    tangentialAccel,
    damping,
    lifetimeMin,
    lifetimeMax,
    burstCount,
    preWarm,
    localSpace,
    sortingMode,
  }), [
    effectName, emissionRate, maxParticles, emitterShape,
    shapeRadius, shapeWidth, shapeHeight, shapeAngle,
    textureType, startSize, endSize, startColor, endColor,
    startOpacity, endOpacity, blendMode,
    speedMin, speedMax, direction, spreadAngle,
    gravityX, gravityY, radialAccel, tangentialAccel, damping,
    lifetimeMin, lifetimeMax,
    burstCount, preWarm, localSpace, sortingMode,
  ]);

  const handleExport = useCallback(() => {
    const config = getCurrentConfig();
    const json = JSON.stringify(config, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${effectName.replace(/\s+/g, '_')}_particle_config.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [effectName, getCurrentConfig]);

  const handleSavePreset = useCallback(() => {
    const config = getCurrentConfig();
    localStorage.setItem(`particle_preset_${effectName}`, JSON.stringify(config));
  }, [effectName, getCurrentConfig]);

  const handleLoadPreset = useCallback(() => {
    const saved = localStorage.getItem(`particle_preset_${effectName}`);
    if (!saved) return;
    try {
      const preset = JSON.parse(saved) as ParticlePreset;
      setEmissionRate(preset.emissionRate);
      setMaxParticles(preset.maxParticles);
      setEmitterShape(preset.emitterShape);
      setShapeRadius(preset.shapeRadius);
      setShapeWidth(preset.shapeWidth);
      setShapeHeight(preset.shapeHeight);
      setShapeAngle(preset.shapeAngle);
      setTextureType(preset.textureType);
      setStartSize(preset.startSize);
      setEndSize(preset.endSize);
      setStartColor(preset.startColor);
      setEndColor(preset.endColor);
      setStartOpacity(preset.startOpacity);
      setEndOpacity(preset.endOpacity);
      setBlendMode(preset.blendMode);
      setSpeedMin(preset.speedMin);
      setSpeedMax(preset.speedMax);
      setDirection(preset.direction);
      setSpreadAngle(preset.spreadAngle);
      setGravityX(preset.gravityX);
      setGravityY(preset.gravityY);
      setRadialAccel(preset.radialAccel);
      setTangentialAccel(preset.tangentialAccel);
      setDamping(preset.damping);
      setLifetimeMin(preset.lifetimeMin);
      setLifetimeMax(preset.lifetimeMax);
      setBurstCount(preset.burstCount);
      setPreWarm(preset.preWarm);
      setLocalSpace(preset.localSpace);
      setSortingMode(preset.sortingMode);
      setActivePreset('');
    } catch { /* ignore parse errors */ }
  }, [effectName]);

  const getEmitterPosition = useCallback(
    (canvasW: number, canvasH: number): [number, number, number?] => {
      const cx = canvasW / 2;
      const cy = canvasH / 2;
      switch (emitterShape) {
        case 'point':
          return [cx, cy];
        case 'line': {
          const angleRad = (shapeAngle * Math.PI) / 180;
          const halfW = shapeWidth / 2;
          const t = Math.random();
          return [cx + Math.cos(angleRad) * (t - 0.5) * shapeWidth, cy + Math.sin(angleRad) * (t - 0.5) * shapeWidth];
        }
        case 'circle': {
          const angle = Math.random() * Math.PI * 2;
          const r = Math.sqrt(Math.random()) * shapeRadius;
          return [cx + Math.cos(angle) * r, cy + Math.sin(angle) * r];
        }
        case 'rect': {
          const x = (Math.random() - 0.5) * shapeWidth;
          const y = (Math.random() - 0.5) * shapeHeight;
          return [cx + x, cy + y];
        }
        case 'cone': {
          const angleRad = ((shapeAngle - spreadAngle / 2 + Math.random() * spreadAngle) * Math.PI) / 180;
          const r = Math.random() * shapeRadius;
          return [cx + Math.cos(angleRad) * r, cy + Math.sin(angleRad) * r];
        }
        case 'ring': {
          const angle = Math.random() * Math.PI * 2;
          return [cx + Math.cos(angle) * shapeRadius, cy + Math.sin(angle) * shapeRadius];
        }
        default:
          return [cx, cy];
      }
    },
    [emitterShape, shapeRadius, shapeWidth, shapeHeight, shapeAngle, spreadAngle],
  );

  const spawnParticle = useCallback(
    (canvasW: number, canvasH: number): Particle => {
      const [px, py] = getEmitterPosition(canvasW, canvasH);
      const dirRad = ((direction + (Math.random() - 0.5) * spreadAngle) * Math.PI) / 180;
      const speed = speedMin + Math.random() * (speedMax - speedMin);
      const life = lifetimeMin + Math.random() * (lifetimeMax - lifetimeMin);
      return {
        x: px,
        y: py,
        vx: Math.cos(dirRad) * speed,
        vy: Math.sin(dirRad) * speed,
        life,
        maxLife: life,
        size: startSize,
        startSize,
        endSize,
        colorStart: startColor,
        colorEnd: endColor,
        alphaStart: startOpacity,
        alphaEnd: endOpacity,
      };
    },
    [
      getEmitterPosition, direction, spreadAngle,
      speedMin, speedMax, lifetimeMin, lifetimeMax,
      startSize, endSize, startColor, endColor,
      startOpacity, endOpacity,
    ],
  );

  const drawParticle = useCallback(
    (ctx: CanvasRenderingContext2D, p: Particle) => {
      const lifeRatio = p.maxLife > 0 ? p.life / p.maxLife : 0;
      const alpha = p.alphaStart + (p.alphaEnd - p.alphaStart) * (1 - lifeRatio);
      const size = p.startSize + (p.endSize - p.startSize) * (1 - lifeRatio);
      const color = lerpColor(p.colorStart, p.colorEnd, 1 - lifeRatio);

      ctx.globalAlpha = Math.max(0, Math.min(1, alpha));

      switch (textureType) {
        case 'square':
          ctx.fillStyle = color;
          ctx.fillRect(p.x - size / 2, p.y - size / 2, size, size);
          break;
        case 'star': {
          ctx.fillStyle = color;
          ctx.beginPath();
          const spikes = 5;
          const outerR = size / 2;
          const innerR = size / 4;
          for (let i = 0; i < spikes * 2; i++) {
            const r = i % 2 === 0 ? outerR : innerR;
            const angle = (i * Math.PI) / spikes - Math.PI / 2;
            const sx = p.x + Math.cos(angle) * r;
            const sy = p.y + Math.sin(angle) * r;
            if (i === 0) ctx.moveTo(sx, sy);
            else ctx.lineTo(sx, sy);
          }
          ctx.closePath();
          ctx.fill();
          break;
        }
        case 'sparkle': {
          ctx.fillStyle = color;
          ctx.beginPath();
          const sr = size / 2;
          for (let i = 0; i < 4; i++) {
            const angle = (i * Math.PI) / 2 - Math.PI / 2;
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(
              p.x + Math.cos(angle) * sr,
              p.y + Math.sin(angle) * sr,
            );
          }
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.5;
          ctx.stroke();
          break;
        }
        case 'circle':
        default:
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(p.x, p.y, Math.max(1, size / 2), 0, Math.PI * 2);
          ctx.fill();
          break;
      }

      ctx.globalAlpha = 1;
    },
    [textureType],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const particleSpawnTimer = { value: 0 };
    let burstApplied = false;

    const loop = (timestamp: number) => {
      if (!lastTimeRef.current) lastTimeRef.current = timestamp;
      const dt = Math.min((timestamp - lastTimeRef.current) / 1000, 0.05);
      lastTimeRef.current = timestamp;

      if (isPlaying) {
        const particles = particlesRef.current;

        if (!burstApplied && burstCount > 0) {
          burstApplied = true;
          for (let i = 0; i < burstCount; i++) {
            if (particles.length < maxParticles) {
              particles.push(spawnParticle(canvas.width, canvas.height));
            }
          }
        }

        particleSpawnTimer.value += dt;
        const spawnInterval = 1 / Math.max(emissionRate, 0.01);
        while (particleSpawnTimer.value >= spawnInterval && particles.length < maxParticles) {
          particleSpawnTimer.value -= spawnInterval;
          particles.push(spawnParticle(canvas.width, canvas.height));
        }

        for (let i = particles.length - 1; i >= 0; i--) {
          const p = particles[i];
          p.life -= dt;
          if (p.life <= 0) {
            particles.splice(i, 1);
            continue;
          }
          p.vx += gravityX * dt;
          p.vy += gravityY * dt;

          const dx = p.x - canvas.width / 2;
          const dy = p.y - canvas.height / 2;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          p.vx += (dx / dist) * radialAccel * dt;
          p.vy += (dy / dist) * radialAccel * dt;

          if (tangentialAccel !== 0) {
            p.vx += (-dy / dist) * tangentialAccel * dt;
            p.vy += (dx / dist) * tangentialAccel * dt;
          }

          p.vx *= damping;
          p.vy *= damping;

          p.x += p.vx * dt;
          p.y += p.vy * dt;

          const lifeRatio = p.maxLife > 0 ? p.life / p.maxLife : 0;
          p.size = p.startSize + (p.endSize - p.startSize) * (1 - lifeRatio);
        }
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (blendMode === 'additive') {
        ctx.globalCompositeOperation = 'lighter';
      } else if (blendMode === 'multiply') {
        ctx.globalCompositeOperation = 'multiply';
      } else {
        ctx.globalCompositeOperation = 'source-over';
      }

      for (const p of particlesRef.current) {
        drawParticle(ctx, p);
      }

      ctx.globalCompositeOperation = 'source-over';
      animFrameRef.current = requestAnimationFrame(loop);
    };

    animFrameRef.current = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener('resize', resizeCanvas);
    };
  }, [
    isPlaying, emissionRate, maxParticles, emitterShape,
    shapeRadius, shapeWidth, shapeHeight, shapeAngle,
    direction, spreadAngle, speedMin, speedMax,
    gravityX, gravityY, radialAccel, tangentialAccel, damping,
    lifetimeMin, lifetimeMax, startSize, endSize,
    startColor, endColor, startOpacity, endOpacity,
    textureType, blendMode, burstCount,
    spawnParticle, drawParticle,
  ]);

  const particleCount = particlesRef.current.length;

  const numInput = (
    value: number,
    setter: (v: number) => void,
    min?: number,
    max?: number,
    step?: number,
  ) => (
    <input
      type="number"
      value={value}
      onChange={e => {
        const v = parseFloat(e.target.value);
        if (!isNaN(v)) setter(v);
      }}
      min={min}
      max={max}
      step={step ?? 1}
      style={styles.input}
    />
  );

  const sliderInput = (
    value: number,
    setter: (v: number) => void,
    min: number,
    max: number,
    step?: number,
  ) => (
    <input
      type="range"
      value={value}
      onChange={e => setter(parseFloat(e.target.value))}
      min={min}
      max={max}
      step={step ?? (max - min) / 100}
      style={{ flex: 1, accentColor: THEME.accent }}
    />
  );

  const renderSection = (title: string, icon: string, children: React.ReactNode) => {
    const collapsed = collapsedSections[title] ?? false;
    return (
      <div style={styles.section}>
        <div style={styles.sectionHeader} onClick={() => toggleSection(title)}>
          <span>
            <i className={icon} style={{ marginRight: 6 }} />
            {title}
          </span>
          <i className={`fas fa-chevron-${collapsed ? 'right' : 'down'}`} style={{ fontSize: 10 }} />
        </div>
        {!collapsed && <div style={styles.sectionBody}>{children}</div>}
      </div>
    );
  };

  const colorField = (label: string, value: string, setter: (v: string) => void) => (
    <div style={styles.row}>
      <span style={styles.label}>{label}</span>
      <input type="color" value={value} onChange={e => setter(e.target.value)} style={styles.colorInput} />
      <input
        type="text"
        value={value}
        onChange={e => setter(e.target.value)}
        style={{ ...styles.input, width: 80 }}
      />
    </div>
  );

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        <i className="fas fa-magic" style={{ color: THEME.accent, fontSize: 16 }} />
        <span style={{ fontWeight: 'bold', fontSize: 13, marginRight: 4 }}>Particle Designer</span>
        <input
          type="text"
          value={effectName}
          onChange={e => setEffectName(e.target.value)}
          style={styles.toolbarInput}
          placeholder="Effect name"
        />
        <button
          style={styles.toolbarBtn}
          onClick={handleSavePreset}
          title="Save current settings to browser storage"
        >
          <i className="fas fa-save" />
          Save Preset
        </button>
        <button
          style={styles.toolbarBtn}
          onClick={handleLoadPreset}
          title="Load saved settings from browser storage"
        >
          <i className="fas fa-folder-open" />
          Load Preset
        </button>
        <button style={styles.toolbarBtn} onClick={handleExport} title="Export as JSON file">
          <i className="fas fa-download" />
          Export Config
        </button>
        <div style={styles.spacer} />
        <button
          style={isPlaying ? styles.toolbarBtnPrimary : styles.toolbarBtn}
          onClick={() => {
            if (!isPlaying) {
              lastTimeRef.current = 0;
              accumulatedRef.current = 0;
            }
            setIsPlaying(!isPlaying);
          }}
        >
          <i className={`fas fa-${isPlaying ? 'pause' : 'play'}`} />
          {isPlaying ? 'Pause' : 'Play'}
        </button>
      </div>

      <div style={styles.body}>
        <div style={styles.leftPanel}>
          <div style={{ display: 'flex', gap: 6, marginBottom: 10, flexWrap: 'wrap' }}>
            {Object.keys(PRESETS).map(key => (
              <button
                key={key}
                style={activePreset === key ? styles.presetBtnActive : styles.presetBtn}
                onClick={() => applyPreset(key)}
              >
                {key}
              </button>
            ))}
          </div>

          {renderSection('Emission', 'fas fa-fire', <>
            <div style={styles.row}>
              <span style={styles.label}>Rate (/sec)</span>
              {numInput(emissionRate, setEmissionRate, 0, 2000, 1)}
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Max Particles</span>
              {numInput(maxParticles, setMaxParticles, 1, 5000, 1)}
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Shape</span>
              <select value={emitterShape} onChange={e => setEmitterShape(e.target.value)} style={styles.select}>
                {EMITTER_SHAPES.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            {(emitterShape === 'circle' || emitterShape === 'cone' || emitterShape === 'ring') && (
              <div style={styles.row}>
                <span style={styles.label}>Radius</span>
                {numInput(shapeRadius, setShapeRadius, 0, 500, 1)}
              </div>
            )}
            {(emitterShape === 'rect' || emitterShape === 'line') && (
              <div style={styles.row}>
                <span style={styles.label}>Width</span>
                {numInput(shapeWidth, setShapeWidth, 0, 800, 1)}
              </div>
            )}
            {emitterShape === 'rect' && (
              <div style={styles.row}>
                <span style={styles.label}>Height</span>
                {numInput(shapeHeight, setShapeHeight, 0, 800, 1)}
              </div>
            )}
            {(emitterShape === 'line' || emitterShape === 'cone') && (
              <div style={styles.row}>
                <span style={styles.label}>Angle</span>
                {numInput(shapeAngle, setShapeAngle, 0, 360, 1)}
              </div>
            )}
          </>)}

          {renderSection('Appearance', 'fas fa-palette', <>
            <div style={styles.row}>
              <span style={styles.label}>Texture</span>
              <select value={textureType} onChange={e => setTextureType(e.target.value)} style={styles.select}>
                {TEXTURE_TYPES.map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            {colorField('Start Color', startColor, setStartColor)}
            {colorField('End Color', endColor, setEndColor)}
            <div style={styles.row}>
              <span style={styles.label}>Start Size</span>
              {sliderInput(startSize, setStartSize, 0.1, 100, 0.1)}
              <span style={{ fontSize: 11, minWidth: 36, textAlign: 'right' }}>{startSize.toFixed(1)}</span>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>End Size</span>
              {sliderInput(endSize, setEndSize, 0.1, 100, 0.1)}
              <span style={{ fontSize: 11, minWidth: 36, textAlign: 'right' }}>{endSize.toFixed(1)}</span>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Start Opacity</span>
              {sliderInput(startOpacity, setStartOpacity, 0, 1, 0.01)}
              <span style={{ fontSize: 11, minWidth: 36, textAlign: 'right' }}>{startOpacity.toFixed(2)}</span>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>End Opacity</span>
              {sliderInput(endOpacity, setEndOpacity, 0, 1, 0.01)}
              <span style={{ fontSize: 11, minWidth: 36, textAlign: 'right' }}>{endOpacity.toFixed(2)}</span>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Blend Mode</span>
              <select value={blendMode} onChange={e => setBlendMode(e.target.value)} style={styles.select}>
                {BLEND_MODES.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          </>)}

          {renderSection('Motion', 'fas fa-arrows-alt', <>
            <div style={styles.row}>
              <span style={styles.label}>Speed Min</span>
              {numInput(speedMin, setSpeedMin, -1000, 1000, 1)}
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Speed Max</span>
              {numInput(speedMax, setSpeedMax, -1000, 2000, 1)}
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Direction</span>
              {numInput(direction, setDirection, -360, 360, 1)}
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Spread</span>
              {sliderInput(spreadAngle, setSpreadAngle, 0, 360, 1)}
              <span style={{ fontSize: 11, minWidth: 36, textAlign: 'right' }}>{spreadAngle}°</span>
            </div>
            <div style={styles.row}>
              <span style={{ ...styles.label, width: 60 }}>Gravity X</span>
              {numInput(gravityX, setGravityX, -500, 500, 1)}
              <span style={{ ...styles.label, width: 60 }}>Y</span>
              {numInput(gravityY, setGravityY, -500, 500, 1)}
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Radial Accel</span>
              {numInput(radialAccel, setRadialAccel, -500, 500, 1)}
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Tang. Accel</span>
              {numInput(tangentialAccel, setTangentialAccel, -500, 500, 1)}
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Damping</span>
              {sliderInput(damping, setDamping, 0.8, 1, 0.001)}
              <span style={{ fontSize: 11, minWidth: 36, textAlign: 'right' }}>{damping.toFixed(3)}</span>
            </div>
          </>)}

          {renderSection('Lifetime', 'fas fa-hourglass-half', <>
            <div style={styles.row}>
              <span style={styles.label}>Min (s)</span>
              {sliderInput(lifetimeMin, setLifetimeMin, 0.01, 10, 0.01)}
              <span style={{ fontSize: 11, minWidth: 36, textAlign: 'right' }}>{lifetimeMin.toFixed(2)}</span>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Max (s)</span>
              {sliderInput(lifetimeMax, setLifetimeMax, 0.01, 20, 0.01)}
              <span style={{ fontSize: 11, minWidth: 36, textAlign: 'right' }}>{lifetimeMax.toFixed(2)}</span>
            </div>
          </>)}

          {renderSection('Advanced', 'fas fa-cogs', <>
            <div style={styles.row}>
              <span style={styles.label}>Burst Count</span>
              {numInput(burstCount, setBurstCount, 0, 1000, 1)}
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Pre-Warm</span>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={preWarm}
                  onChange={e => setPreWarm(e.target.checked)}
                  style={{ accentColor: THEME.accent }}
                />
                <span style={{ fontSize: 11 }}>{preWarm ? 'On' : 'Off'}</span>
              </label>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Local Space</span>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={localSpace}
                  onChange={e => setLocalSpace(e.target.checked)}
                  style={{ accentColor: THEME.accent }}
                />
                <span style={{ fontSize: 11 }}>{localSpace ? 'On' : 'Off'}</span>
              </label>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>Sorting</span>
              <select value={sortingMode} onChange={e => setSortingMode(e.target.value)} style={styles.select}>
                {SORTING_MODES.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </>)}
        </div>

        <div style={styles.rightPanel}>
          <canvas
            ref={canvasRef}
            style={{ width: '100%', height: '100%' }}
          />
          <div style={styles.canvasOverlay}>
            Particles: {particleCount} / {maxParticles}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParticleDesigner;