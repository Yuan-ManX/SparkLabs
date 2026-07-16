import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'layers' | 'presets' | 'mix';

interface AudioLayer {
  id: string;
  name: string;
  volume: number;
  x: number;
  y: number;
  z: number;
}

interface MixPreset {
  id: string;
  name: string;
  layer_count: number;
}

interface MixRule {
  id: string;
  name: string;
  condition: string;
  action: string;
}

interface ActiveMix {
  id: string;
  name: string;
  layer_count: number;
  master_volume: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AudioLayeringPanel: React.FC = () => {
  const [layers, setLayers] = useState<AudioLayer[]>([]);
  const [presets, setPresets] = useState<MixPreset[]>([]);
  const [mixRules, setMixRules] = useState<MixRule[]>([]);
  const [activeMix, setActiveMix] = useState<ActiveMix | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('layers');

  const [layerName, setLayerName] = useState('');
  const [layerVolume, setLayerVolume] = useState('0.8');
  const [spatialX, setSpatialX] = useState('0');
  const [spatialY, setSpatialY] = useState('0');
  const [spatialZ, setSpatialZ] = useState('0');

  const [presetName, setPresetName] = useState('');
  const [presetLayer, setPresetLayer] = useState('');
  const [applyPreset, setApplyPreset] = useState('');

  const [ruleName, setRuleName] = useState('');
  const [ruleCondition, setRuleCondition] = useState('');
  const [ruleAction, setRuleAction] = useState('');
  const [masterVolume, setMasterVolume] = useState('0.8');
  const [duckTarget, setDuckTarget] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultLayers: AudioLayer[] = [
    { id: uid(), name: 'Music', volume: 0.8, x: 0, y: 0, z: 0 },
    { id: uid(), name: 'SFX', volume: 0.9, x: 5, y: 2, z: -3 },
    { id: uid(), name: 'Ambient', volume: 0.5, x: 0, y: 0, z: 0 },
    { id: uid(), name: 'Voice', volume: 1.0, x: 2, y: 1, z: 0 },
  ];

  const defaultPresets: MixPreset[] = [
    { id: uid(), name: 'Combat', layer_count: 3 },
    { id: uid(), name: 'Exploration', layer_count: 2 },
    { id: uid(), name: 'Menu', layer_count: 1 },
  ];

  const defaultMixRules: MixRule[] = [
    { id: uid(), name: 'DuckSFX', condition: 'voice_active', action: 'lower_sfx' },
    { id: uid(), name: 'CombatBoost', condition: 'in_combat', action: 'boost_music' },
  ];

  const defaultActiveMix: ActiveMix = {
    id: uid(), name: 'CurrentMix', layer_count: 4, master_volume: 0.8,
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchActiveMix = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/audio-layering/get_active_mix`);
      const data = await res.json();
      if (data.mix) setActiveMix(data.mix);
      setMessage(null);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setLayers(defaultLayers);
    setPresets(defaultPresets);
    setMixRules(defaultMixRules);
    setActiveMix(defaultActiveMix);
    fetchActiveMix();
  }, [fetchActiveMix]);

  const handleCreateLayer = async () => {
    if (!layerName.trim()) {
      showMessage('Layer name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/audio-layering/create_layer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: layerName, volume: parseFloat(layerVolume) }),
      });
      const newLayer: AudioLayer = {
        id: uid(), name: layerName, volume: parseFloat(layerVolume), x: 0, y: 0, z: 0,
      };
      setLayers(prev => [...prev, newLayer]);
      setLayerName('');
      showMessage(`Layer "${layerName}" created`, 'success');
    } catch {
      const newLayer: AudioLayer = {
        id: uid(), name: layerName, volume: parseFloat(layerVolume), x: 0, y: 0, z: 0,
      };
      setLayers(prev => [...prev, newLayer]);
      setLayerName('');
      showMessage(`Layer "${layerName}" created (offline fallback)`, 'info');
    }
  };

  const handleSetSpatialPosition = async () => {
    try {
      await fetch(`${apiBase}/audio-layering/set_spatial_position`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          layer: layers[0]?.name || 'Music',
          x: parseFloat(spatialX), y: parseFloat(spatialY), z: parseFloat(spatialZ),
        }),
      });
      showMessage(`Spatial position set to (${spatialX}, ${spatialY}, ${spatialZ})`, 'success');
    } catch {
      showMessage(`Spatial position set to (${spatialX}, ${spatialY}, ${spatialZ}) (offline fallback)`, 'info');
    }
  };

  const handleCreateMixPreset = async () => {
    if (!presetName.trim()) {
      showMessage('Preset name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/audio-layering/create_mix_preset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: presetName }),
      });
      const newPreset: MixPreset = { id: uid(), name: presetName, layer_count: 0 };
      setPresets(prev => [...prev, newPreset]);
      setPresetName('');
      showMessage(`Mix preset "${presetName}" created`, 'success');
    } catch {
      const newPreset: MixPreset = { id: uid(), name: presetName, layer_count: 0 };
      setPresets(prev => [...prev, newPreset]);
      setPresetName('');
      showMessage(`Mix preset "${presetName}" created (offline fallback)`, 'info');
    }
  };

  const handleAddLayerToPreset = async () => {
    if (!presetLayer.trim()) {
      showMessage('Layer name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/audio-layering/add_layer_to_preset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset: presets[0]?.name || 'Combat', layer: presetLayer }),
      });
      setPresets(prev => prev.map(p => p.name === (presets[0]?.name || 'Combat') ? { ...p, layer_count: p.layer_count + 1 } : p));
      setPresetLayer('');
      showMessage(`Layer "${presetLayer}" added to preset`, 'success');
    } catch {
      setPresets(prev => prev.map(p => p.name === (presets[0]?.name || 'Combat') ? { ...p, layer_count: p.layer_count + 1 } : p));
      setPresetLayer('');
      showMessage(`Layer "${presetLayer}" added to preset (offline fallback)`, 'info');
    }
  };

  const handleApplyPreset = async () => {
    if (!applyPreset.trim()) {
      showMessage('Preset name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/audio-layering/apply_preset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset: applyPreset }),
      });
      showMessage(`Preset "${applyPreset}" applied`, 'success');
    } catch {
      showMessage(`Preset "${applyPreset}" applied (offline fallback)`, 'info');
    }
    setApplyPreset('');
  };

  const handleSeedDefaultPresets = async () => {
    try {
      await fetch(`${apiBase}/audio-layering/seed_default_presets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      showMessage('Default presets seeded', 'success');
    } catch {
      showMessage('Default presets seeded (offline fallback)', 'info');
    }
  };

  const handleSetMixRule = async () => {
    if (!ruleName.trim()) {
      showMessage('Rule name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/audio-layering/set_mix_rule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: ruleName, condition: ruleCondition, action: ruleAction }),
      });
      const newRule: MixRule = {
        id: uid(), name: ruleName, condition: ruleCondition, action: ruleAction,
      };
      setMixRules(prev => [...prev, newRule]);
      setRuleName('');
      setRuleCondition('');
      setRuleAction('');
      showMessage(`Mix rule "${ruleName}" set`, 'success');
    } catch {
      const newRule: MixRule = {
        id: uid(), name: ruleName, condition: ruleCondition, action: ruleAction,
      };
      setMixRules(prev => [...prev, newRule]);
      setRuleName('');
      setRuleCondition('');
      setRuleAction('');
      showMessage(`Mix rule "${ruleName}" set (offline fallback)`, 'info');
    }
  };

  const handleCrossfadeLayers = async () => {
    try {
      await fetch(`${apiBase}/audio-layering/crossfade_layers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration: 2.0 }),
      });
      showMessage('Crossfade executed (2.0s)', 'success');
    } catch {
      showMessage('Crossfade executed (2.0s) (offline fallback)', 'info');
    }
  };

  const handleDuckLayer = async () => {
    if (!duckTarget.trim()) {
      showMessage('Layer name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/audio-layering/duck_layer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layer: duckTarget, amount: 0.5 }),
      });
      showMessage(`Layer "${duckTarget}" ducked by 50%`, 'success');
    } catch {
      showMessage(`Layer "${duckTarget}" ducked by 50% (offline fallback)`, 'info');
    }
    setDuckTarget('');
  };

  const handleSetMasterVolume = async () => {
    try {
      await fetch(`${apiBase}/audio-layering/set_master_volume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ volume: parseFloat(masterVolume) }),
      });
      setActiveMix(prev => prev ? { ...prev, master_volume: parseFloat(masterVolume) } : prev);
      showMessage(`Master volume set to ${masterVolume}`, 'success');
    } catch {
      setActiveMix(prev => prev ? { ...prev, master_volume: parseFloat(masterVolume) } : prev);
      showMessage(`Master volume set to ${masterVolume} (offline fallback)`, 'info');
    }
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'layers', label: 'Layers', icon: '\uD83C\uDFB5', count: layers.length },
    { key: 'presets', label: 'Presets', icon: '\uD83D\uDCCB', count: presets.length },
    { key: 'mix', label: 'Mix', icon: '\uD83C\uDF9B\uFE0F', count: mixRules.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD0A'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Audio Layering</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {layers.length} layers · {presets.length} presets · {mixRules.length} rules
          </span>
          {activeMix && (
            <span style={{ fontSize: 10, color: '#6bcb77' }}>
              Master: {(activeMix.master_volume * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'layers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83C\uDFB5'} create_layer
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={layerName} onChange={e => setLayerName(e.target.value)} placeholder="e.g. Music" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Volume</div>
                  <input value={layerVolume} onChange={e => setLayerVolume(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 70,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateLayer} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>set_spatial_position</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>X</div>
                  <input value={spatialX} onChange={e => setSpatialX(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Y</div>
                  <input value={spatialY} onChange={e => setSpatialY(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Z</div>
                  <input value={spatialZ} onChange={e => setSpatialZ(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleSetSpatialPosition} style={{
                  padding: '6px 14px', backgroundColor: '#3a2d3a', color: '#a29bfe',
                  border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Set Position</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDFB5'} Layers <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({layers.length})</span>
            </div>
            {layers.map(layer => (
              <div key={layer.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{layer.name}</span>
                  <div style={{
                    width: 60, height: 4, backgroundColor: '#111', borderRadius: 2, overflow: 'hidden',
                  }}>
                    <div style={{
                      width: `${layer.volume * 100}%`, height: '100%',
                      backgroundColor: layer.volume > 0.7 ? '#6bcb77' : layer.volume > 0.4 ? '#fdcb6e' : '#ff6b6b',
                      borderRadius: 2,
                    }} />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Vol: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{layer.volume}</span></span>
                  <span>Pos: <span style={{ color: '#a29bfe', fontWeight: 600 }}>({layer.x}, {layer.y}, {layer.z})</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'presets' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCB'} create_mix_preset
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={presetName} onChange={e => setPresetName(e.target.value)} placeholder="e.g. Combat" style={{
                    padding: '6px 10px', fontSize: 11, width: 180,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateMixPreset} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 160,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>add_layer_to_preset</div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Layer Name</div>
                    <input value={presetLayer} onChange={e => setPresetLayer(e.target.value)} placeholder="e.g. SFX" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <button onClick={handleAddLayerToPreset} style={{
                    padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                    border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                  }}>Add</button>
                </div>
              </div>

              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 160,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>apply_preset</div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Preset</div>
                    <input value={applyPreset} onChange={e => setApplyPreset(e.target.value)} placeholder="e.g. Combat" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <button onClick={handleApplyPreset} style={{
                    padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                    border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                  }}>Apply</button>
                </div>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>seed_default_presets</div>
              <button onClick={handleSeedDefaultPresets} style={{
                padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                fontSize: 11, fontWeight: 600,
              }}>Seed Defaults</button>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCCB'} Presets <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({presets.length})</span>
            </div>
            {presets.map(preset => (
              <div key={preset.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{preset.name}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>
                  Layers: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{preset.layer_count}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'mix' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83C\uDF9B\uFE0F'} set_mix_rule
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={ruleName} onChange={e => setRuleName(e.target.value)} placeholder="e.g. DuckSFX" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Condition</div>
                  <input value={ruleCondition} onChange={e => setRuleCondition(e.target.value)} placeholder="e.g. voice_active" style={{
                    padding: '6px 10px', fontSize: 11, width: 130,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Action</div>
                  <input value={ruleAction} onChange={e => setRuleAction(e.target.value)} placeholder="e.g. lower_sfx" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleSetMixRule} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Set Rule</button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 150,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>crossfade_layers</div>
                <button onClick={handleCrossfadeLayers} style={{
                  padding: '6px 14px', backgroundColor: '#3a2d3a', color: '#a29bfe',
                  border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Crossfade</button>
              </div>

              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 150,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>duck_layer</div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Layer</div>
                    <input value={duckTarget} onChange={e => setDuckTarget(e.target.value)} placeholder="e.g. SFX" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#111', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <button onClick={handleDuckLayer} style={{
                    padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                    border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                  }}>Duck</button>
                </div>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>
                {'\uD83D\uDD0A'} set_master_volume
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Master Volume (0-1)</div>
                  <input value={masterVolume} onChange={e => setMasterVolume(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleSetMasterVolume} style={{
                  padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
                  border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Set Master</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDF9B\uFE0F'} get_active_mix
            </div>
            {activeMix && (
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{activeMix.name}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Layers: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{activeMix.layer_count}</span></span>
                  <span>Master Vol: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{(activeMix.master_volume * 100).toFixed(0)}%</span></span>
                </div>
                <div style={{ marginTop: 6 }}>
                  <div style={{
                    width: '100%', height: 4, backgroundColor: '#111', borderRadius: 2, overflow: 'hidden',
                  }}>
                    <div style={{
                      width: `${activeMix.master_volume * 100}%`, height: '100%',
                      backgroundColor: '#6bcb77', borderRadius: 2,
                    }} />
                  </div>
                </div>
              </div>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83C\uDF9B\uFE0F'} Mix Rules <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({mixRules.length})</span>
            </div>
            {mixRules.map(rule => (
              <div key={rule.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{rule.name}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>
                  <span>If <span style={{ color: '#fdcb6e' }}>{rule.condition}</span></span>
                  {' → '}
                  <span style={{ color: '#6bcb77' }}>{rule.action}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDD0A'} {layers.length} layers · {presets.length} presets · {mixRules.length} rules</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default AudioLayeringPanel;