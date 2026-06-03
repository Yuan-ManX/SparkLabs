import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'pipeline' | 'passes' | 'postfx' | 'stats';
type RenderQuality = 'low' | 'medium' | 'high' | 'ultra';

interface RenderPass {
  pass_id: string;
  name: string;
  order: number;
  enabled: boolean;
  description: string;
  pass_type: string;
}

interface PostProcessEffect {
  effect_id: string;
  name: string;
  effect_type: string;
  enabled: boolean;
  intensity: number;
  description: string;
}

interface RenderStats {
  frame_id: number;
  frame_time_ms: number;
  draw_calls: number;
  triangle_count: number;
  passes_rendered: number;
  memory_mb: number;
  timestamp: string;
}

interface PipelineStats {
  total_passes: number;
  active_passes: number;
  total_effects: number;
  active_effects: number;
  current_quality: RenderQuality;
  current_fps: number;
  target_fps: number;
  resolution_scale: number;
  average_frame_time: number;
  total_frames: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const QUALITY_COLORS: Record<RenderQuality, string> = {
  low: '#888',
  medium: '#fdcb6e',
  high: '#6bcb77',
  ultra: '#a29bfe',
};

const QUALITY_LABELS: Record<RenderQuality, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  ultra: 'Ultra',
};

const RenderPipelinePanel: React.FC = () => {
  const [passes, setPasses] = useState<RenderPass[]>([]);
  const [effects, setEffects] = useState<PostProcessEffect[]>([]);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [frameStats, setFrameStats] = useState<RenderStats[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('pipeline');

  const [quality, setQuality] = useState<RenderQuality>('high');
  const [loadingQuality, setLoadingQuality] = useState(false);
  const [loadingRender, setLoadingRender] = useState(false);

  const apiBase = 'http://localhost:8000/api/agent/render-pipeline';

  const defaultPasses: RenderPass[] = [
    { pass_id: uid(), name: 'Shadow Map', order: 0, enabled: true, description: 'Renders depth maps from light perspectives for shadow casting', pass_type: 'shadow' },
    { pass_id: uid(), name: 'GBuffer', order: 1, enabled: true, description: 'Writes albedo, normal, roughness, and metallic to render targets', pass_type: 'deferred' },
    { pass_id: uid(), name: 'SSAO', order: 2, enabled: true, description: 'Screen-space ambient occlusion for contact shadows', pass_type: 'post_process' },
    { pass_id: uid(), name: 'Lighting', order: 3, enabled: true, description: 'Accumulates direct and indirect lighting contributions', pass_type: 'lighting' },
    { pass_id: uid(), name: 'Translucency', order: 4, enabled: true, description: 'Renders transparent and translucent geometry', pass_type: 'forward' },
    { pass_id: uid(), name: 'Particle', order: 5, enabled: true, description: 'Renders GPU particle systems with depth sorting', pass_type: 'forward' },
    { pass_id: uid(), name: 'Post Process', order: 6, enabled: true, description: 'Applies post-processing effects in sequence', pass_type: 'post_process' },
    { pass_id: uid(), name: 'UI Overlay', order: 7, enabled: true, description: 'Renders screen-space UI elements on top', pass_type: 'ui' },
  ];

  const defaultEffects: PostProcessEffect[] = [
    { effect_id: uid(), name: 'Bloom', effect_type: 'bloom', enabled: true, intensity: 0.7, description: 'Adds glowing light bleed around bright areas' },
    { effect_id: uid(), name: 'Motion Blur', effect_type: 'motion_blur', enabled: true, intensity: 0.4, description: 'Camera-based motion blur for cinematic feel' },
    { effect_id: uid(), name: 'Depth of Field', effect_type: 'dof', enabled: true, intensity: 0.3, description: 'Bokeh depth of field with focal plane control' },
    { effect_id: uid(), name: 'Color Grading', effect_type: 'color_grading', enabled: true, intensity: 0.6, description: 'LUT-based color grading for atmosphere' },
    { effect_id: uid(), name: 'Vignette', effect_type: 'vignette', enabled: true, intensity: 0.5, description: 'Darkens screen edges to focus attention' },
    { effect_id: uid(), name: 'SSR', effect_type: 'ssr', enabled: true, intensity: 0.5, description: 'Screen-space reflections on glossy surfaces' },
    { effect_id: uid(), name: 'Film Grain', effect_type: 'film_grain', enabled: false, intensity: 0.1, description: 'Adds cinematic film grain noise' },
    { effect_id: uid(), name: 'Chromatic Aberration', effect_type: 'chromatic_aberr', enabled: false, intensity: 0.15, description: 'Color fringing at screen edges' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      setStats({ ...data, current_quality: data.current_quality || 'high' });
    } catch {
      setStats({ total_passes: defaultPasses.length, active_passes: defaultPasses.filter(p => p.enabled).length, total_effects: defaultEffects.length, active_effects: defaultEffects.filter(e => e.enabled).length, current_quality: 'high', current_fps: 60, target_fps: 60, resolution_scale: 1.0, average_frame_time: 16.67, total_frames: 0 });
    }
  }, []);

  const fetchPasses = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/passes`);
      const data = await res.json();
      if (data.passes && data.passes.length > 0) setPasses(data.passes);
    } catch {}
  }, []);

  const fetchEffects = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/post-processes`);
      const data = await res.json();
      if (data.effects && data.effects.length > 0) setEffects(data.effects);
    } catch {}
  }, []);

  useEffect(() => {
    setPasses(defaultPasses);
    setEffects(defaultEffects);
    fetchStats();
    fetchPasses();
    fetchEffects();
  }, [fetchStats, fetchPasses, fetchEffects]);

  const handleRenderFrame = async () => {
    setLoadingRender(true);
    try {
      const res = await fetch(`${apiBase}/render-frame`, { method: 'POST' });
      const data = await res.json();
      const fStat: RenderStats = {
        frame_id: data.frame_id || (frameStats.length + 1),
        frame_time_ms: data.frame_time_ms ?? (14 + Math.random() * 6),
        draw_calls: data.draw_calls ?? Math.floor(200 + Math.random() * 300),
        triangle_count: data.triangle_count ?? Math.floor(50000 + Math.random() * 100000),
        passes_rendered: data.passes_rendered ?? passes.filter(p => p.enabled).length,
        memory_mb: data.memory_mb ?? Math.floor(300 + Math.random() * 200),
        timestamp: 'just now',
      };
      setFrameStats(prev => [fStat, ...prev].slice(0, 20));
      showMessage(`Frame ${fStat.frame_id} rendered in ${fStat.frame_time_ms.toFixed(1)}ms`, 'success');
      fetchStats();
    } catch {
      const fStat: RenderStats = {
        frame_id: frameStats.length + 1,
        frame_time_ms: 14 + Math.random() * 6,
        draw_calls: Math.floor(200 + Math.random() * 300),
        triangle_count: Math.floor(50000 + Math.random() * 100000),
        passes_rendered: passes.filter(p => p.enabled).length,
        memory_mb: Math.floor(300 + Math.random() * 200),
        timestamp: 'just now',
      };
      setFrameStats(prev => [fStat, ...prev].slice(0, 20));
      showMessage('Frame rendered (offline mode)', 'info');
    } finally { setLoadingRender(false); }
  };

  const handleSetQuality = async (newQuality: RenderQuality) => {
    setLoadingQuality(true);
    try {
      await fetch(`${apiBase}/set-quality`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quality: newQuality }),
      });
      setQuality(newQuality);
      showMessage(`Quality set to ${QUALITY_LABELS[newQuality]}`, 'success');
      fetchStats();
    } catch {
      setQuality(newQuality);
      showMessage(`Quality set to ${QUALITY_LABELS[newQuality]} (offline mode)`, 'info');
    } finally { setLoadingQuality(false); }
  };

  const handleToggleEffect = async (effectId: string) => {
    const effect = effects.find(e => e.effect_id === effectId);
    if (!effect) return;
    try {
      await fetch(`${apiBase}/set-post-process`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ effect_type: effect.effect_type, enabled: !effect.enabled }),
      });
      setEffects(prev => prev.map(e => e.effect_id === effectId ? { ...e, enabled: !e.enabled } : e));
      showMessage(`"${effect.name}" ${effect.enabled ? 'disabled' : 'enabled'}`, 'info');
    } catch {
      setEffects(prev => prev.map(e => e.effect_id === effectId ? { ...e, enabled: !e.enabled } : e));
    }
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'pipeline', label: 'Pipeline', icon: '\uD83C\uDFAC', count: passes.length },
    { key: 'passes', label: 'Passes', icon: '\uD83D\uDCCB', count: passes.filter(p => p.enabled).length },
    { key: 'postfx', label: 'Post FX', icon: '\u2728', count: effects.filter(e => e.enabled).length },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA', count: frameStats.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAC'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Render Pipeline</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && <span style={{ fontSize: 10, color: '#888' }}>{stats.current_fps} FPS · {QUALITY_LABELS[stats.current_quality]}</span>}
        </div>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ padding: '8px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <button onClick={handleRenderFrame} disabled={loadingRender} style={{ padding: '6px 12px', backgroundColor: loadingRender ? '#1a2a3a' : '#2563eb', color: loadingRender ? '#666' : '#fff', border: 'none', borderRadius: 4, cursor: loadingRender ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600 }}>
          {loadingRender ? 'Rendering...' : '\u25B6 Render Frame'}
        </button>
        <div style={{ display: 'flex', gap: 2 }}>
          {(Object.keys(QUALITY_LABELS) as RenderQuality[]).map(q => (
            <button key={q} onClick={() => handleSetQuality(q)} disabled={loadingQuality} style={{ padding: '4px 8px', fontSize: 10, fontWeight: 600, backgroundColor: quality === q ? QUALITY_COLORS[q] + '33' : '#141428', color: quality === q ? QUALITY_COLORS[q] : '#666', border: `1px solid ${quality === q ? QUALITY_COLORS[q] : '#333'}`, borderRadius: 3, cursor: loadingQuality ? 'not-allowed' : 'pointer' }}>
              {QUALITY_LABELS[q]}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #74b9ff' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'pipeline' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {stats && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCCA'} Performance</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8 }}>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>FPS</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: stats.current_fps >= 60 ? '#6bcb77' : stats.current_fps >= 30 ? '#fdcb6e' : '#ff6b6b' }}>{stats.current_fps}</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Frame Time</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>{stats.average_frame_time.toFixed(1)}ms</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Quality</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: QUALITY_COLORS[stats.current_quality] }}>{QUALITY_LABELS[stats.current_quality]}</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Resolution</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#a29bfe' }}>{(stats.resolution_scale * 100).toFixed(0)}%</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Passes</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>{stats.active_passes}/{stats.total_passes}</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Total Frames</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#e17055' }}>{stats.total_frames}</div>
                  </div>
                </div>
              </div>
            )}

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD17'} Pipeline Flow</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {passes.map((p, i) => (
                  <div key={p.pass_id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', backgroundColor: '#141428', borderRadius: 4 }}>
                    <span style={{ fontSize: 10, color: '#666', fontWeight: 700, width: 20 }}>{i + 1}</span>
                    <span style={{ fontSize: '8px', padding: '1px 4px', borderRadius: 2, backgroundColor: p.pass_type === 'shadow' ? '#1a1a3a' : p.pass_type === 'deferred' ? '#1a2a3a' : p.pass_type === 'lighting' ? '#3a3a1a' : p.pass_type === 'forward' ? '#2a3a1a' : p.pass_type === 'post_process' ? '#3a1a3a' : '#1a3a2a', color: p.pass_type === 'shadow' ? '#a29bfe' : p.pass_type === 'deferred' ? '#74b9ff' : p.pass_type === 'lighting' ? '#fdcb6e' : p.pass_type === 'forward' ? '#6bcb77' : p.pass_type === 'post_process' ? '#fd79a8' : '#00b894', fontWeight: 600, textTransform: 'uppercase' }}>{p.pass_type}</span>
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#ccc' }}>{p.name}</span>
                    <span style={{ flex: 1 }} />
                    <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: p.enabled ? '#6bcb77' : '#888' }} />
                    {i < passes.length - 1 && <span style={{ fontSize: 8, color: '#555', padding: '0 10px' }}>{'\u2193'}</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'passes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {passes.map(pass => (
              <div key={pass.pass_id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${pass.enabled ? '#6bcb77' : '#888'}`, opacity: pass.enabled ? 1 : 0.6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, color: '#666', fontWeight: 700 }}>#{pass.order}</span>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{pass.name}</span>
                    <span style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: pass.pass_type === 'deferred' ? '#1a2a3a' : pass.pass_type === 'shadow' ? '#1a1a3a' : '#141428', color: pass.pass_type === 'deferred' ? '#74b9ff' : pass.pass_type === 'shadow' ? '#a29bfe' : '#888', fontWeight: 600, textTransform: 'uppercase' }}>{pass.pass_type}</span>
                  </div>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: pass.enabled ? '#6bcb77' : '#888' }} />
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>{pass.description}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'postfx' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {effects.map(effect => (
              <div key={effect.effect_id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${effect.enabled ? '#fd79a8' : '#888'}`, opacity: effect.enabled ? 1 : 0.6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{effect.name}</span>
                    <span style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#3a1a3a', color: '#fd79a8', fontWeight: 600 }}>{effect.effect_type}</span>
                  </div>
                  <button onClick={() => handleToggleEffect(effect.effect_id)} style={{ padding: '3px 10px', fontSize: 10, fontWeight: 600, backgroundColor: effect.enabled ? '#1a3a1a' : '#1a2a3a', color: effect.enabled ? '#6bcb77' : '#888', border: `1px solid ${effect.enabled ? '#2d5a2d' : '#333'}`, borderRadius: 3, cursor: 'pointer' }}>
                    {effect.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>{effect.description}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 9, color: '#666', width: 50 }}>Intensity</span>
                  <div style={{ flex: 1, height: 4, backgroundColor: '#141428', borderRadius: 2 }}>
                    <div style={{ height: '100%', width: `${effect.intensity * 100}%`, backgroundColor: effect.enabled ? '#fd79a8' : '#555', borderRadius: 2 }} />
                  </div>
                  <span style={{ fontSize: 9, fontWeight: 600, color: effect.enabled ? '#fd79a8' : '#888' }}>{(effect.intensity * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {frameStats.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCA'}</span>
                Click "Render Frame" to see performance stats
              </div>
            )}
            {frameStats.map(fs => (
              <div key={fs.frame_id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${fs.frame_time_ms < 16.67 ? '#6bcb77' : fs.frame_time_ms < 33.33 ? '#fdcb6e' : '#ff6b6b'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 12 }}>Frame #{fs.frame_id}</span>
                  <span style={{ fontSize: 10, color: '#666' }}>{fs.timestamp}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: 6 }}>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 3, textAlign: 'center' }}>
                    <div style={{ fontSize: 8, color: '#666', textTransform: 'uppercase' }}>Time</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: fs.frame_time_ms < 16.67 ? '#6bcb77' : fs.frame_time_ms < 33.33 ? '#fdcb6e' : '#ff6b6b' }}>{fs.frame_time_ms.toFixed(1)}ms</div>
                  </div>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 3, textAlign: 'center' }}>
                    <div style={{ fontSize: 8, color: '#666', textTransform: 'uppercase' }}>Draw Calls</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#74b9ff' }}>{fs.draw_calls}</div>
                  </div>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 3, textAlign: 'center' }}>
                    <div style={{ fontSize: 8, color: '#666', textTransform: 'uppercase' }}>Triangles</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#a29bfe' }}>{(fs.triangle_count / 1000).toFixed(1)}k</div>
                  </div>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 3, textAlign: 'center' }}>
                    <div style={{ fontSize: 8, color: '#666', textTransform: 'uppercase' }}>Passes</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e' }}>{fs.passes_rendered}</div>
                  </div>
                  <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 3, textAlign: 'center' }}>
                    <div style={{ fontSize: 8, color: '#666', textTransform: 'uppercase' }}>Memory</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#e17055' }}>{fs.memory_mb}MB</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83C\uDFAC'} {passes.filter(p => p.enabled).length} passes · {effects.filter(e => e.enabled).length} effects active</span>
        <span>{stats ? `${stats.current_fps} FPS @ ${QUALITY_LABELS[stats.current_quality]}` : 'Connected'}</span>
      </div>
    </div>
  );
};

export default RenderPipelinePanel;