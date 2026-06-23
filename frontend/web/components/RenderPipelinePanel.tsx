"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Monitor, Layers, Zap, Camera, Image, Code2, Gauge,
  BarChart3, Sun, Moon, CloudLightning, ToggleLeft, ToggleRight,
  RefreshCw, CheckCircle2, Circle, Loader2, Sliders, Box
} from 'lucide-react';

// Tab identifiers
type TabId = 'passes' | 'materials' | 'shaders' | 'stats' | 'lights' | 'postfx';

// Quality preset type
type QualityPreset = 'low' | 'medium' | 'high' | 'ultra';

// Render pass
interface RenderPass {
  id: string;
  name: string;
  pass_type: string;
  enabled: boolean;
  order: number;
  description: string;
}

// Material entry
interface MaterialEntry {
  id: string;
  name: string;
  shader: string;
  texture_count: number;
  parameter_count: number;
}

// Built-in shader
interface BuiltInShader {
  id: string;
  name: string;
  shader_type: 'vertex' | 'fragment' | 'compute' | 'geometry';
  compiled: boolean;
  variant_count: number;
}

// Render queue statistics
interface RenderQueueStats {
  draw_calls: number;
  batches: number;
  culled: number;
  triangles: number;
  vertices: number;
}

// Light configuration
interface LightConfig {
  id: string;
  name: string;
  light_type: 'directional' | 'point' | 'spot' | 'area';
  enabled: boolean;
  intensity: number;
  color: string;
  casts_shadows: boolean;
}

// Post-processing effect
interface PostEffect {
  id: string;
  name: string;
  effect_type: string;
  enabled: boolean;
  intensity: number;
  settings: Record<string, number>;
  description: string;
}

// Performance metrics
interface PerformanceMetrics {
  fps: number;
  frame_time_ms: number;
  gpu_memory_mb: number;
  cpu_usage_percent: number;
  draw_calls: number;
  triangles: number;
}

// Engine status response
interface EngineStatus {
  render_stats: RenderQueueStats;
  performance: PerformanceMetrics;
  quality: QualityPreset;
  passes: RenderPass[];
  materials: MaterialEntry[];
  shaders: BuiltInShader[];
  lights: LightConfig[];
  post_effects: PostEffect[];
}

// Helper for unique IDs
const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const QUALITY_PRESETS: { key: QualityPreset; label: string; color: string }[] = [
  { key: 'low', label: 'Low', color: '#888' },
  { key: 'medium', label: 'Medium', color: '#fdcb6e' },
  { key: 'high', label: 'High', color: '#6bcb77' },
  { key: 'ultra', label: 'Ultra', color: '#a29bfe' },
];

const RenderPipelinePanel: React.FC = () => {
  // Tab state
  const [activeTab, setActiveTab] = useState<TabId>('passes');

  // Render passes
  const [passes, setPasses] = useState<RenderPass[]>([]);

  // Materials
  const [materials, setMaterials] = useState<MaterialEntry[]>([]);

  // Shaders
  const [shaders, setShaders] = useState<BuiltInShader[]>([]);

  // Render queue stats
  const [queueStats, setQueueStats] = useState<RenderQueueStats | null>(null);

  // Lights
  const [lights, setLights] = useState<LightConfig[]>([]);

  // Post effects
  const [postEffects, setPostEffects] = useState<PostEffect[]>([]);

  // Performance metrics
  const [perfMetrics, setPerfMetrics] = useState<PerformanceMetrics | null>(null);

  // Quality preset
  const [quality, setQuality] = useState<QualityPreset>('high');
  const [isSettingQuality, setIsSettingQuality] = useState(false);

  // UI state
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const apiBase = 'http://localhost:8000/api/engine';

  // Default render passes
  const defaultPasses: RenderPass[] = [
    { id: uid(), name: 'Shadow Map', pass_type: 'shadow', enabled: true, order: 0, description: 'Depth maps from light perspectives' },
    { id: uid(), name: 'GBuffer', pass_type: 'deferred', enabled: true, order: 1, description: 'Albedo, normal, roughness, metallic' },
    { id: uid(), name: 'SSAO', pass_type: 'post_process', enabled: true, order: 2, description: 'Screen-space ambient occlusion' },
    { id: uid(), name: 'Lighting', pass_type: 'lighting', enabled: true, order: 3, description: 'Direct and indirect lighting' },
    { id: uid(), name: 'Translucency', pass_type: 'forward', enabled: true, order: 4, description: 'Transparent geometry' },
    { id: uid(), name: 'Particle', pass_type: 'forward', enabled: true, order: 5, description: 'GPU particle systems' },
    { id: uid(), name: 'Post Process', pass_type: 'post_process', enabled: true, order: 6, description: 'Post-processing effects' },
    { id: uid(), name: 'UI Overlay', pass_type: 'ui', enabled: true, order: 7, description: 'Screen-space UI elements' },
  ];

  // Default materials
  const defaultMaterials: MaterialEntry[] = [
    { id: uid(), name: 'Standard PBR', shader: 'Standard', texture_count: 3, parameter_count: 8 },
    { id: uid(), name: 'Toon Shading', shader: 'Toon', texture_count: 1, parameter_count: 5 },
    { id: uid(), name: 'Water Surface', shader: 'Water', texture_count: 4, parameter_count: 12 },
    { id: uid(), name: 'Terrain Blended', shader: 'Terrain', texture_count: 6, parameter_count: 10 },
    { id: uid(), name: 'Glass Refractive', shader: 'Glass', texture_count: 2, parameter_count: 7 },
    { id: uid(), name: 'Emissive Glow', shader: 'Emissive', texture_count: 1, parameter_count: 4 },
  ];

  // Default shaders
  const defaultShaders: BuiltInShader[] = [
    { id: uid(), name: 'Standard Vertex', shader_type: 'vertex', compiled: true, variant_count: 12 },
    { id: uid(), name: 'PBR Fragment', shader_type: 'fragment', compiled: true, variant_count: 8 },
    { id: uid(), name: 'Shadow Caster', shader_type: 'vertex', compiled: true, variant_count: 4 },
    { id: uid(), name: 'Particle Compute', shader_type: 'compute', compiled: true, variant_count: 3 },
    { id: uid(), name: 'Terrain Geometry', shader_type: 'geometry', compiled: true, variant_count: 2 },
    { id: uid(), name: 'PostFX Fragment', shader_type: 'fragment', compiled: true, variant_count: 6 },
  ];

  // Default lights
  const defaultLights: LightConfig[] = [
    { id: uid(), name: 'Sun', light_type: 'directional', enabled: true, intensity: 1.0, color: '#ffeedd', casts_shadows: true },
    { id: uid(), name: 'Ambient', light_type: 'point', enabled: true, intensity: 0.3, color: '#aaccff', casts_shadows: false },
    { id: uid(), name: 'Player Torch', light_type: 'spot', enabled: true, intensity: 0.8, color: '#ffcc88', casts_shadows: true },
    { id: uid(), name: 'Area Light 1', light_type: 'area', enabled: false, intensity: 0.5, color: '#ffffff', casts_shadows: false },
  ];

  // Default post effects
  const defaultPostEffects: PostEffect[] = [
    { id: uid(), name: 'Bloom', effect_type: 'bloom', enabled: true, intensity: 0.6, settings: { threshold: 0.8, radius: 4 }, description: 'Glow around bright areas' },
    { id: uid(), name: 'Motion Blur', effect_type: 'motion_blur', enabled: true, intensity: 0.3, settings: { samples: 8, shutter_speed: 0.5 }, description: 'Camera-based motion blur' },
    { id: uid(), name: 'Depth of Field', effect_type: 'dof', enabled: true, intensity: 0.4, settings: { focal_distance: 10, aperture: 2.8 }, description: 'Bokeh depth of field' },
    { id: uid(), name: 'Color Grading', effect_type: 'color_grading', enabled: true, intensity: 0.7, settings: { contrast: 1.1, saturation: 1.0 }, description: 'LUT-based color grading' },
    { id: uid(), name: 'Vignette', effect_type: 'vignette', enabled: true, intensity: 0.4, settings: { radius: 0.8, smoothness: 0.5 }, description: 'Darken screen edges' },
    { id: uid(), name: 'SSR', effect_type: 'ssr', enabled: true, intensity: 0.5, settings: { max_steps: 64, thickness: 0.5 }, description: 'Screen-space reflections' },
    { id: uid(), name: 'Film Grain', effect_type: 'film_grain', enabled: false, intensity: 0.1, settings: { amount: 0.05, size: 2 }, description: 'Cinematic film grain' },
    { id: uid(), name: 'Chromatic Aberration', effect_type: 'chromatic_aberr', enabled: false, intensity: 0.15, settings: { amount: 0.02, center_fade: 0.5 }, description: 'Color fringing at edges' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // Fetch engine status
  const fetchEngineStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/status`);
      const data: EngineStatus = await res.json();
      if (data.passes) setPasses(data.passes);
      if (data.materials) setMaterials(data.materials);
      if (data.shaders) setShaders(data.shaders);
      if (data.render_stats) setQueueStats(data.render_stats);
      if (data.lights) setLights(data.lights);
      if (data.post_effects) setPostEffects(data.post_effects);
      if (data.performance) setPerfMetrics(data.performance);
      if (data.quality) setQuality(data.quality);
    } catch {
      // Use defaults
      if (passes.length === 0) setPasses(defaultPasses);
      if (materials.length === 0) setMaterials(defaultMaterials);
      if (shaders.length === 0) setShaders(defaultShaders);
      if (!queueStats) setQueueStats({ draw_calls: 245, batches: 32, culled: 156, triangles: 125000, vertices: 98000 });
      if (lights.length === 0) setLights(defaultLights);
      if (postEffects.length === 0) setPostEffects(defaultPostEffects);
      if (!perfMetrics) setPerfMetrics({ fps: 60, frame_time_ms: 16.67, gpu_memory_mb: 512, cpu_usage_percent: 35, draw_calls: 245, triangles: 125000 });
    }
  }, []);

  // Initialize
  useEffect(() => {
    setPasses(defaultPasses);
    setMaterials(defaultMaterials);
    setShaders(defaultShaders);
    setLights(defaultLights);
    setPostEffects(defaultPostEffects);
    setQueueStats({ draw_calls: 245, batches: 32, culled: 156, triangles: 125000, vertices: 98000 });
    setPerfMetrics({ fps: 60, frame_time_ms: 16.67, gpu_memory_mb: 512, cpu_usage_percent: 35, draw_calls: 245, triangles: 125000 });
    fetchEngineStatus();
    const interval = setInterval(fetchEngineStatus, 15000);
    return () => clearInterval(interval);
  }, [fetchEngineStatus]);

  // Toggle render pass
  const handleTogglePass = (passId: string) => {
    setPasses(prev => prev.map(p => p.id === passId ? { ...p, enabled: !p.enabled } : p));
    const pass = passes.find(p => p.id === passId);
    if (pass) showMessage(`"${pass.name}" ${pass.enabled ? 'disabled' : 'enabled'}`, 'info');
  };

  // Toggle light
  const handleToggleLight = (lightId: string) => {
    setLights(prev => prev.map(l => l.id === lightId ? { ...l, enabled: !l.enabled } : l));
  };

  // Toggle post effect
  const handleToggleEffect = (effectId: string) => {
    setPostEffects(prev => prev.map(e => e.id === effectId ? { ...e, enabled: !e.enabled } : e));
  };

  // Set quality preset
  const handleSetQuality = async (newQuality: QualityPreset) => {
    setIsSettingQuality(true);
    try {
      await fetch(`${apiBase}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quality: newQuality }),
      });
      setQuality(newQuality);
      showMessage(`Quality set to ${newQuality.toUpperCase()}`, 'success');
    } catch {
      setQuality(newQuality);
      showMessage(`Quality set to ${newQuality.toUpperCase()} (offline mode)`, 'info');
    } finally {
      setIsSettingQuality(false);
    }
  };

  // Get pass type color
  const getPassTypeColor = (passType: string) => {
    switch (passType) {
      case 'shadow': return 'text-[#a29bfe] bg-[#a29bfe]/10';
      case 'deferred': return 'text-[#74b9ff] bg-[#74b9ff]/10';
      case 'lighting': return 'text-[#fdcb6e] bg-[#fdcb6e]/10';
      case 'forward': return 'text-[#6bcb77] bg-[#6bcb77]/10';
      case 'post_process': return 'text-[#fd79a8] bg-[#fd79a8]/10';
      case 'ui': return 'text-[#00d4ff] bg-[#00d4ff]/10';
      default: return 'text-[#888] bg-[#888]/10';
    }
  };

  // Get shader type icon
  const getShaderTypeIcon = (type: string) => {
    switch (type) {
      case 'vertex': return 'V';
      case 'fragment': return 'F';
      case 'compute': return 'C';
      case 'geometry': return 'G';
      default: return '?';
    }
  };

  const getShaderTypeColor = (type: string) => {
    switch (type) {
      case 'vertex': return 'text-[#6bcb77] bg-[#6bcb77]/10';
      case 'fragment': return 'text-[#fd79a8] bg-[#fd79a8]/10';
      case 'compute': return 'text-[#fdcb6e] bg-[#fdcb6e]/10';
      case 'geometry': return 'text-[#a29bfe] bg-[#a29bfe]/10';
      default: return 'text-[#888] bg-[#888]/10';
    }
  };

  // Get light type icon
  const getLightIcon = (type: string) => {
    switch (type) {
      case 'directional': return <Sun className="w-3.5 h-3.5" />;
      case 'point': return <Zap className="w-3.5 h-3.5" />;
      case 'spot': return <CloudLightning className="w-3.5 h-3.5" />;
      case 'area': return <Box className="w-3.5 h-3.5" />;
      default: return <Zap className="w-3.5 h-3.5" />;
    }
  };

  // Tab definitions
  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'passes', label: 'Passes', icon: <Layers className="w-3.5 h-3.5" /> },
    { key: 'materials', label: 'Materials', icon: <Image className="w-3.5 h-3.5" /> },
    { key: 'shaders', label: 'Shaders', icon: <Code2 className="w-3.5 h-3.5" /> },
    { key: 'stats', label: 'Queue', icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { key: 'lights', label: 'Lights', icon: <Sun className="w-3.5 h-3.5" /> },
    { key: 'postfx', label: 'Post FX', icon: <Sliders className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#1a1a2e] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#0f3460]/50 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Monitor className="w-[18px] h-[18px] text-[#00d4ff]" />
          <span className="font-bold text-[15px]">Render Pipeline</span>
        </div>
        <div className="flex items-center gap-2">
          {perfMetrics && (
            <span className="text-[10px] text-[#888]">
              {perfMetrics.fps} FPS · {quality.toUpperCase()}
            </span>
          )}
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#0f3460]/30 border-[#00d4ff]/30 text-[#00d4ff]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#0f3460]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Quality presets + Performance bar */}
      <div className="px-4 py-2 border-b border-[#0f3460]/50 flex items-center gap-3 bg-[#16213e]/50">
        <span className="text-[10px] text-[#666] uppercase tracking-wider font-semibold">Quality:</span>
        <div className="flex gap-1">
          {QUALITY_PRESETS.map(preset => (
            <button
              key={preset.key}
              onClick={() => handleSetQuality(preset.key)}
              disabled={isSettingQuality}
              className="px-3 py-1 rounded text-[10px] font-semibold transition-all disabled:opacity-50"
              style={{
                backgroundColor: quality === preset.key ? `${preset.color}20` : '#1a1a2e',
                border: `1px solid ${quality === preset.key ? preset.color : '#0f3460'}`,
                color: quality === preset.key ? preset.color : '#666',
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        {perfMetrics && (
          <div className="flex items-center gap-4 text-[10px]">
            <span className="flex items-center gap-1">
              <Gauge className="w-3 h-3 text-[#6bcb77]" />
              <span className="text-[#6bcb77] font-semibold">{perfMetrics.fps}</span>
              <span className="text-[#666]">FPS</span>
            </span>
            <span className="flex items-center gap-1">
              <Zap className="w-3 h-3 text-[#fdcb6e]" />
              <span className="text-[#fdcb6e] font-semibold">{perfMetrics.frame_time_ms.toFixed(1)}</span>
              <span className="text-[#666]">ms</span>
            </span>
            <span className="flex items-center gap-1">
              <Box className="w-3 h-3 text-[#a29bfe]" />
              <span className="text-[#a29bfe] font-semibold">{perfMetrics.gpu_memory_mb}</span>
              <span className="text-[#666]">MB</span>
            </span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#0f3460]/50 overflow-x-auto">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors whitespace-nowrap ${
              activeTab === tab.key
                ? 'bg-[#16213e] text-[#00d4ff] border-b-2 border-[#00d4ff]'
                : 'text-[#888] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {/* ==================== PASSES TAB ==================== */}
        {activeTab === 'passes' && (
          <div className="flex flex-col gap-2">
            {passes.map((pass, idx) => (
              <div
                key={pass.id}
                className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3"
                style={{ opacity: pass.enabled ? 1 : 0.5 }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-[#666] w-5">#{pass.order}</span>
                    <span className="text-[12px] font-semibold text-[#ccc]">{pass.name}</span>
                    <span className={`text-[8px] font-semibold uppercase px-1.5 py-0.5 rounded ${getPassTypeColor(pass.pass_type)}`}>
                      {pass.pass_type}
                    </span>
                  </div>
                  <button
                    onClick={() => handleTogglePass(pass.id)}
                    className="transition-colors"
                  >
                    {pass.enabled ? (
                      <ToggleRight className="w-5 h-5 text-[#6bcb77]" />
                    ) : (
                      <ToggleLeft className="w-5 h-5 text-[#555]" />
                    )}
                  </button>
                </div>
                <div className="text-[10px] text-[#888] mt-1">{pass.description}</div>
                {/* Connector */}
                {idx < passes.length - 1 && (
                  <div className="flex justify-center mt-1 text-[#333] text-[10px]">↓</div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* ==================== MATERIALS TAB ==================== */}
        {activeTab === 'materials' && (
          <div className="grid grid-cols-2 gap-2">
            {materials.map(material => (
              <div
                key={material.id}
                className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3 hover:border-[#0f3460]/60 transition-all cursor-pointer"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Image className="w-3.5 h-3.5 text-[#fdcb6e]" />
                  <span className="text-[11px] font-semibold text-[#ccc] truncate">{material.name}</span>
                </div>
                <div className="text-[9px] text-[#888] mb-1">Shader: {material.shader}</div>
                <div className="flex gap-3 text-[9px]">
                  <span className="text-[#00d4ff]">{material.texture_count} textures</span>
                  <span className="text-[#a29bfe]">{material.parameter_count} params</span>
                </div>
              </div>
            ))}
            {materials.length === 0 && (
              <div className="col-span-2 flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <Image className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No materials loaded</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== SHADERS TAB ==================== */}
        {activeTab === 'shaders' && (
          <div className="flex flex-col gap-2">
            {shaders.map(shader => (
              <div
                key={shader.id}
                className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <span className={`w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold ${getShaderTypeColor(shader.shader_type)}`}>
                    {getShaderTypeIcon(shader.shader_type)}
                  </span>
                  <div>
                    <div className="text-[12px] font-semibold text-[#ccc]">{shader.name}</div>
                    <div className="text-[9px] text-[#666]">{shader.shader_type} · {shader.variant_count} variants</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {shader.compiled ? (
                    <CheckCircle2 className="w-4 h-4 text-[#6bcb77]" />
                  ) : (
                    <Circle className="w-4 h-4 text-[#e94560]" />
                  )}
                  <span className={`text-[9px] font-semibold ${shader.compiled ? 'text-[#6bcb77]' : 'text-[#e94560]'}`}>
                    {shader.compiled ? 'Compiled' : 'Error'}
                  </span>
                </div>
              </div>
            ))}
            {shaders.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <Code2 className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No shaders available</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== QUEUE STATS TAB ==================== */}
        {activeTab === 'stats' && (
          <div className="flex flex-col gap-3">
            {/* Performance metrics */}
            {perfMetrics && (
              <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Gauge className="w-3.5 h-3.5 text-[#00d4ff]" />
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Performance</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">FPS</div>
                    <div className="text-[18px] font-bold text-[#6bcb77]">{perfMetrics.fps}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Frame Time</div>
                    <div className="text-[18px] font-bold text-[#fdcb6e]">{perfMetrics.frame_time_ms.toFixed(1)}ms</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">GPU Mem</div>
                    <div className="text-[18px] font-bold text-[#a29bfe]">{perfMetrics.gpu_memory_mb}MB</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">CPU</div>
                    <div className="text-[18px] font-bold text-[#e17055]">{perfMetrics.cpu_usage_percent}%</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Draw Calls</div>
                    <div className="text-[18px] font-bold text-[#00d4ff]">{perfMetrics.draw_calls}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 text-center border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Triangles</div>
                    <div className="text-[18px] font-bold text-[#fd79a8]">{(perfMetrics.triangles / 1000).toFixed(1)}k</div>
                  </div>
                </div>
              </div>
            )}

            {/* Render queue stats */}
            {queueStats && (
              <div className="bg-[#16213e] rounded-lg border border-[#0f3460]/50 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <BarChart3 className="w-3.5 h-3.5 text-[#00d4ff]" />
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Render Queue</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-[#1a1a2e] rounded-md p-2 border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Draw Calls</div>
                    <div className="text-[16px] font-bold text-[#00d4ff]">{queueStats.draw_calls}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Batches</div>
                    <div className="text-[16px] font-bold text-[#6bcb77]">{queueStats.batches}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Culled</div>
                    <div className="text-[16px] font-bold text-[#e94560]">{queueStats.culled}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 border border-[#0f3460]/20">
                    <div className="text-[8px] text-[#666] uppercase">Vertices</div>
                    <div className="text-[16px] font-bold text-[#a29bfe]">{(queueStats.vertices / 1000).toFixed(1)}k</div>
                  </div>
                </div>
                {/* Visual bar: draw calls vs culled */}
                <div className="mt-2">
                  <div className="flex justify-between text-[9px] text-[#666] mb-0.5">
                    <span>Draw Calls</span>
                    <span>Culled</span>
                  </div>
                  <div className="flex h-3 rounded-full overflow-hidden bg-[#1a1a2e]">
                    <div className="bg-[#00d4ff] flex items-center justify-center text-[8px] font-semibold" style={{ width: `${(queueStats.draw_calls / (queueStats.draw_calls + queueStats.culled)) * 100}%` }}>
                      {queueStats.draw_calls}
                    </div>
                    <div className="bg-[#e94560] flex items-center justify-center text-[8px] font-semibold" style={{ width: `${(queueStats.culled / (queueStats.draw_calls + queueStats.culled)) * 100}%` }}>
                      {queueStats.culled}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <button
              onClick={fetchEngineStatus}
              className="flex items-center justify-center gap-2 py-2 bg-[#16213e] border border-[#0f3460]/50 text-[#888] rounded-lg text-[12px] hover:border-[#0f3460] transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Statistics
            </button>
          </div>
        )}

        {/* ==================== LIGHTS TAB ==================== */}
        {activeTab === 'lights' && (
          <div className="flex flex-col gap-2">
            {lights.map(light => (
              <div
                key={light.id}
                className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3"
                style={{ opacity: light.enabled ? 1 : 0.5 }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[#fdcb6e]">{getLightIcon(light.light_type)}</span>
                    <span className="text-[12px] font-semibold text-[#ccc]">{light.name}</span>
                    <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded bg-[#1a1a2e] text-[#fdcb6e]">
                      {light.light_type}
                    </span>
                  </div>
                  <button onClick={() => handleToggleLight(light.id)}>
                    {light.enabled ? (
                      <ToggleRight className="w-5 h-5 text-[#6bcb77]" />
                    ) : (
                      <ToggleLeft className="w-5 h-5 text-[#555]" />
                    )}
                  </button>
                </div>
                <div className="flex items-center gap-4 text-[10px] text-[#888]">
                  <span>Intensity: <span className="text-[#fdcb6e]">{light.intensity.toFixed(1)}</span></span>
                  <span className="flex items-center gap-1">
                    Color:
                    <span className="w-3 h-3 rounded-full border border-[#0f3460]" style={{ backgroundColor: light.color }} />
                  </span>
                  <span className="flex items-center gap-1">
                    Shadows:
                    {light.casts_shadows ? (
                      <CheckCircle2 className="w-3 h-3 text-[#6bcb77]" />
                    ) : (
                      <Circle className="w-3 h-3 text-[#555]" />
                    )}
                  </span>
                </div>
              </div>
            ))}
            {lights.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <Sun className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No lights in scene</span>
              </div>
            )}
          </div>
        )}

        {/* ==================== POST FX TAB ==================== */}
        {activeTab === 'postfx' && (
          <div className="flex flex-col gap-2">
            {postEffects.map(effect => (
              <div
                key={effect.id}
                className="bg-[#16213e] rounded-lg border border-[#0f3460]/30 p-3"
                style={{ opacity: effect.enabled ? 1 : 0.5 }}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-3.5 h-3.5 text-[#fd79a8]" />
                    <span className="text-[12px] font-semibold text-[#ccc]">{effect.name}</span>
                    <span className="text-[8px] font-semibold uppercase px-1.5 py-0.5 rounded bg-[#fd79a8]/10 text-[#fd79a8]">
                      {effect.effect_type}
                    </span>
                  </div>
                  <button onClick={() => handleToggleEffect(effect.id)}>
                    {effect.enabled ? (
                      <ToggleRight className="w-5 h-5 text-[#6bcb77]" />
                    ) : (
                      <ToggleLeft className="w-5 h-5 text-[#555]" />
                    )}
                  </button>
                </div>
                <div className="text-[10px] text-[#888] mb-2">{effect.description}</div>
                {/* Intensity slider */}
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[9px] text-[#666] w-12">Intensity</span>
                  <div className="flex-1 h-1.5 bg-[#1a1a2e] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${effect.intensity * 100}%`,
                        backgroundColor: effect.enabled ? '#fd79a8' : '#555',
                      }}
                    />
                  </div>
                  <span className="text-[9px] font-semibold text-[#fd79a8] w-8 text-right">
                    {(effect.intensity * 100).toFixed(0)}%
                  </span>
                </div>
                {/* Settings */}
                <div className="flex flex-wrap gap-2 mt-1">
                  {Object.entries(effect.settings).map(([key, value]) => (
                    <span key={key} className="text-[9px] bg-[#1a1a2e] rounded px-1.5 py-0.5 border border-[#0f3460]/20 text-[#888]">
                      {key}: <span className="text-[#aaa]">{value}</span>
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {postEffects.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#0f3460]/30">
                <Sliders className="w-10 h-10 mb-2 opacity-20" />
                <span className="text-[12px]">No post-processing effects</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-[#0f3460]/50 bg-[#141428] flex items-center justify-between text-[10px] text-[#666]">
        <span className="flex items-center gap-1">
          <Monitor className="w-3 h-3" />
          {passes.filter(p => p.enabled).length} passes · {lights.filter(l => l.enabled).length} lights · {postEffects.filter(e => e.enabled).length} fx
        </span>
        <span>Auto-refresh: 15s</span>
      </div>
    </div>
  );
};

export default RenderPipelinePanel;