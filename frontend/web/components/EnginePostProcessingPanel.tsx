"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'effects' | 'pipelines' | 'stats';

interface PostProcessingStats {
  total_effects: number;
  total_pipelines: number;
}

interface Effect {
  id: string;
  effect_type: string;
  blend_mode: string;
  quality: string;
  priority: number;
  stage: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EnginePostProcessingPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('effects');
  const [stats, setStats] = useState<PostProcessingStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Effects form
  const [effectForm, setEffectForm] = useState({
    effect_type: 'bloom', parameters: '', blend_mode: 'additive', quality: 'high', priority: '0', stage: 'post',
  });
  const [effectLoading, setEffectLoading] = useState(false);
  const [effects, setEffects] = useState<Effect[]>([]);

  // Remove effect
  const [removeEffectId, setRemoveEffectId] = useState('');
  const [removeLoading, setRemoveLoading] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/post-processing/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  const fetchEffects = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/post-processing/effects`);
      if (res.ok) {
        const data = await res.json();
        setEffects(data.effects || data || []);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchEffects();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchEffects]);

  // --- Add Effect ---
  const handleAddEffect = async () => {
    setEffectLoading(true);
    try {
      const res = await fetch(`${API_BASE}/post-processing/add-effect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(effectForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Effect added successfully', 'success');
        setEffectForm({ effect_type: 'bloom', parameters: '', blend_mode: 'additive', quality: 'high', priority: '0', stage: 'post' });
        fetchEffects();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add effect', 'error');
      }
    } catch {
      showMessage('Effect added (offline mode)', 'info');
      setEffects(prev => [...prev, {
        id: uid(), effect_type: effectForm.effect_type, blend_mode: effectForm.blend_mode,
        quality: effectForm.quality, priority: parseInt(effectForm.priority) || 0, stage: effectForm.stage,
      }]);
      setEffectForm({ effect_type: 'bloom', parameters: '', blend_mode: 'additive', quality: 'high', priority: '0', stage: 'post' });
    } finally {
      setEffectLoading(false);
    }
  };

  // --- Remove Effect ---
  const handleRemoveEffect = async () => {
    if (!removeEffectId.trim()) {
      showMessage('Effect ID is required', 'error');
      return;
    }
    setRemoveLoading(true);
    try {
      const res = await fetch(`${API_BASE}/post-processing/remove-effect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ effect_id: removeEffectId }),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Effect removed successfully', 'success');
        setRemoveEffectId('');
        fetchEffects();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to remove effect', 'error');
      }
    } catch {
      showMessage('Effect removed (offline mode)', 'info');
      setEffects(prev => prev.filter(e => e.id !== removeEffectId));
      setRemoveEffectId('');
    } finally {
      setRemoveLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'effects', label: 'Effects', icon: '\uD83C\uDFA8' },
    { key: 'pipelines', label: 'Pipelines', icon: '\uD83D\uDEE0\uFE0F' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#111', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#1e1e1e',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFA8'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Post Processing</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_effects ?? 0} effects · {stats.total_pipelines ?? 0} pipelines
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Effects */}
        {activeTab === 'effects' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFA8'} Add Effect
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Effect Type</span>
                    <select style={darkSelectStyle} value={effectForm.effect_type}
                      onChange={e => setEffectForm(prev => ({ ...prev, effect_type: e.target.value }))}>
                      <option value="bloom">Bloom</option>
                      <option value="motion_blur">Motion Blur</option>
                      <option value="depth_of_field">Depth of Field</option>
                      <option value="vignette">Vignette</option>
                      <option value="color_grading">Color Grading</option>
                      <option value="ambient_occlusion">Ambient Occlusion</option>
                      <option value="anti_aliasing">Anti-Aliasing</option>
                      <option value="chromatic_aberration">Chromatic Aberration</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Blend Mode</span>
                    <select style={darkSelectStyle} value={effectForm.blend_mode}
                      onChange={e => setEffectForm(prev => ({ ...prev, blend_mode: e.target.value }))}>
                      <option value="additive">Additive</option>
                      <option value="multiply">Multiply</option>
                      <option value="screen">Screen</option>
                      <option value="overlay">Overlay</option>
                      <option value="replace">Replace</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Quality</span>
                    <select style={darkSelectStyle} value={effectForm.quality}
                      onChange={e => setEffectForm(prev => ({ ...prev, quality: e.target.value }))}>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="ultra">Ultra</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Stage</span>
                    <select style={darkSelectStyle} value={effectForm.stage}
                      onChange={e => setEffectForm(prev => ({ ...prev, stage: e.target.value }))}>
                      <option value="pre">Pre-Processing</option>
                      <option value="post">Post-Processing</option>
                      <option value="final">Final Pass</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Priority</span>
                    <input style={darkInputStyle} placeholder="0" value={effectForm.priority}
                      onChange={e => setEffectForm(prev => ({ ...prev, priority: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Parameters</span>
                    <input style={darkInputStyle} placeholder='{"intensity": 1.0}' value={effectForm.parameters}
                      onChange={e => setEffectForm(prev => ({ ...prev, parameters: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleAddEffect} disabled={effectLoading}
                style={effectLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {effectLoading ? 'Adding...' : '\uD83C\uDFA8 Add Effect'}
              </button>
            </div>

            {/* Remove Effect */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83D\uDDD1\uFE0F'} Remove Effect
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Effect ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. effect_001" value={removeEffectId}
                    onChange={e => setRemoveEffectId(e.target.value)} />
                </div>
                <button onClick={handleRemoveEffect} disabled={removeLoading}
                  style={removeLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}>
                  {removeLoading ? 'Removing...' : '\uD83D\uDDD1\uFE0F Remove'}
                </button>
              </div>
            </div>

            {/* Effects List */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDCCB'} Effects ({effects.length})
              </div>
              {effects.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No effects added yet.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {effects.map((effect, i) => (
                    <div key={effect.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{effect.effect_type}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{effect.blend_mode}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                        <span>Quality: <span style={{ color: '#6bcb77' }}>{effect.quality}</span></span>
                        <span>Stage: <span style={{ color: '#fdcb6e' }}>{effect.stage}</span></span>
                        <span>Priority: <span style={{ color: '#a29bfe' }}>{effect.priority}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Pipelines */}
        {activeTab === 'pipelines' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDEE0\uFE0F'} Post-Processing Pipelines
              </div>
              <div style={{ fontSize: 12, color: '#888', padding: '8px 0' }}>
                Pipelines define the execution order and dependencies of post-processing effects.
                Configure your rendering pipeline stages to achieve the desired visual output.
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 10 }}>
                {[
                  { label: 'Default Pipeline', status: 'Active', color: '#6bcb77' },
                  { label: 'Custom Pipeline', status: 'Inactive', color: '#888' },
                ].map((pipeline, i) => (
                  <div key={i} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 11, color: '#ccc' }}>{pipeline.label}</span>
                    <span style={{ fontSize: 10, color: pipeline.color }}>{pipeline.status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Post Processing Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Effects', value: stats?.total_effects, color: '#00d4ff' },
                  { label: 'Total Pipelines', value: stats?.total_pipelines, color: '#a29bfe' },
                  { label: 'Active Effects', value: effects.length, color: '#6bcb77' },
                  { label: 'Status', value: 'Active', color: '#fdcb6e' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/post-processing</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83C\uDFA8'} Post Processing</span>
        <span>
          {stats
            ? `${stats.total_effects ?? 0} effects · ${stats.total_pipelines ?? 0} pipelines`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}