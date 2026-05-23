import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'config' | 'events' | 'sequences';

interface TransitionConfig {
  id: string;
  name: string;
  type: string;
  duration: number;
}

interface ActiveTransition {
  id: string;
  config_name: string;
  progress: number;
  status: string;
}

interface SequenceStep {
  id: string;
  order: number;
  config_name: string;
  delay: number;
}

interface Sequence {
  id: string;
  name: string;
  step_count: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SceneTransitionPanel: React.FC = () => {
  const [configs, setConfigs] = useState<TransitionConfig[]>([]);
  const [activeTransitions, setActiveTransitions] = useState<ActiveTransition[]>([]);
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [history, setHistory] = useState<ActiveTransition[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('config');

  const [configName, setConfigName] = useState('');
  const [configType, setConfigType] = useState('FADE');
  const [configDuration, setConfigDuration] = useState('1.0');

  const [effectName, setEffectName] = useState('');

  const [transitionConfig, setTransitionConfig] = useState('');
  const [progressValue, setProgressValue] = useState('0.5');
  const [cancelTarget, setCancelTarget] = useState('');

  const [sequenceName, setSequenceName] = useState('');
  const [stepConfig, setStepConfig] = useState('');
  const [stepDelay, setStepDelay] = useState('0.5');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultConfigs: TransitionConfig[] = [
    { id: uid(), name: 'CrossFade', type: 'FADE', duration: 1.0 },
    { id: uid(), name: 'SlideLeft', type: 'SLIDE', duration: 0.6 },
    { id: uid(), name: 'ZoomIn', type: 'ZOOM', duration: 0.8 },
    { id: uid(), name: 'WipeDown', type: 'WIPE', duration: 0.5 },
  ];

  const defaultActive: ActiveTransition[] = [
    { id: uid(), config_name: 'CrossFade', progress: 0.45, status: 'running' },
    { id: uid(), config_name: 'SlideLeft', progress: 0.0, status: 'pending' },
  ];

  const defaultSequences: Sequence[] = [
    { id: uid(), name: 'IntroSequence', step_count: 3 },
    { id: uid(), name: 'GameOverSequence', step_count: 2 },
  ];

  const defaultHistory: ActiveTransition[] = [
    { id: uid(), config_name: 'FadeIn', progress: 1.0, status: 'completed' },
    { id: uid(), config_name: 'SlideRight', progress: 1.0, status: 'cancelled' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/scene-transition/get_transition_history`);
      const data = await res.json();
      if (data.history) setHistory(data.history);
      setMessage(null);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setConfigs(defaultConfigs);
    setActiveTransitions(defaultActive);
    setSequences(defaultSequences);
    setHistory(defaultHistory);
    fetchHistory();
  }, [fetchHistory]);

  const handleConfigureTransition = async () => {
    if (!configName.trim()) {
      showMessage('Config name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/scene-transition/configure_transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: configName, type: configType, duration: parseFloat(configDuration),
        }),
      });
      const newConfig: TransitionConfig = {
        id: uid(), name: configName, type: configType, duration: parseFloat(configDuration),
      };
      setConfigs(prev => [...prev, newConfig]);
      setConfigName('');
      showMessage(`Transition "${configName}" configured`, 'success');
    } catch {
      const newConfig: TransitionConfig = {
        id: uid(), name: configName, type: configType, duration: parseFloat(configDuration),
      };
      setConfigs(prev => [...prev, newConfig]);
      setConfigName('');
      showMessage(`Transition "${configName}" configured (offline fallback)`, 'info');
    }
  };

  const handlePreviewEffect = async () => {
    if (!effectName.trim()) {
      showMessage('Effect name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/scene-transition/preview_effect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ effect: effectName }),
      });
      showMessage(`Effect "${effectName}" previewed`, 'success');
    } catch {
      showMessage(`Effect "${effectName}" previewed (offline fallback)`, 'info');
    }
    setEffectName('');
  };

  const handleStartTransition = async () => {
    if (!transitionConfig.trim()) {
      showMessage('Config name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/scene-transition/start_transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: transitionConfig }),
      });
      const newActive: ActiveTransition = {
        id: uid(), config_name: transitionConfig, progress: 0, status: 'running',
      };
      setActiveTransitions(prev => [...prev, newActive]);
      showMessage(`Transition "${transitionConfig}" started`, 'success');
    } catch {
      const newActive: ActiveTransition = {
        id: uid(), config_name: transitionConfig, progress: 0, status: 'running',
      };
      setActiveTransitions(prev => [...prev, newActive]);
      showMessage(`Transition "${transitionConfig}" started (offline fallback)`, 'info');
    }
    setTransitionConfig('');
  };

  const handleUpdateProgress = async () => {
    try {
      await fetch(`${apiBase}/scene-transition/update_progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ progress: parseFloat(progressValue) }),
      });
      showMessage(`Progress updated to ${progressValue}`, 'success');
    } catch {
      showMessage(`Progress updated to ${progressValue} (offline fallback)`, 'info');
    }
  };

  const handleCancelTransition = async () => {
    if (!cancelTarget.trim()) {
      showMessage('Config name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/scene-transition/cancel_transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: cancelTarget }),
      });
      setActiveTransitions(prev => prev.map(t => t.config_name === cancelTarget ? { ...t, status: 'cancelled' } : t));
      showMessage(`Transition "${cancelTarget}" cancelled`, 'success');
    } catch {
      showMessage(`Transition "${cancelTarget}" cancelled (offline fallback)`, 'info');
    }
    setCancelTarget('');
  };

  const handleCreateSequence = async () => {
    if (!sequenceName.trim()) {
      showMessage('Sequence name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/scene-transition/create_sequence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sequenceName }),
      });
      const newSeq: Sequence = { id: uid(), name: sequenceName, step_count: 0 };
      setSequences(prev => [...prev, newSeq]);
      setSequenceName('');
      showMessage(`Sequence "${sequenceName}" created`, 'success');
    } catch {
      const newSeq: Sequence = { id: uid(), name: sequenceName, step_count: 0 };
      setSequences(prev => [...prev, newSeq]);
      setSequenceName('');
      showMessage(`Sequence "${sequenceName}" created (offline fallback)`, 'info');
    }
  };

  const handleAddStepToSequence = async () => {
    if (!stepConfig.trim()) {
      showMessage('Config name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/scene-transition/add_step_to_sequence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sequence: sequences[0]?.name || 'IntroSequence', config: stepConfig, delay: parseFloat(stepDelay) }),
      });
      setSequences(prev => prev.map(s => s.name === (sequences[0]?.name || 'IntroSequence') ? { ...s, step_count: s.step_count + 1 } : s));
      showMessage(`Step "${stepConfig}" added to sequence`, 'success');
    } catch {
      showMessage(`Step "${stepConfig}" added to sequence (offline fallback)`, 'info');
    }
    setStepConfig('');
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'config', label: 'Config', icon: '\u2699\uFE0F', count: configs.length },
    { key: 'events', label: 'Events', icon: '\u25B6\uFE0F', count: activeTransitions.length },
    { key: 'sequences', label: 'Sequences', icon: '\uD83D\uDD17', count: sequences.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFAC'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Scene Transitions</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {configs.length} configs · {activeTransitions.length} active · {sequences.length} sequences
          </span>
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
        {activeTab === 'config' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u2699\uFE0F'} configure_transition
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={configName} onChange={e => setConfigName(e.target.value)} placeholder="e.g. CrossFade" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={configType} onChange={e => setConfigType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="FADE">Fade</option>
                    <option value="SLIDE">Slide</option>
                    <option value="ZOOM">Zoom</option>
                    <option value="WIPE">Wipe</option>
                    <option value="DISSOLVE">Dissolve</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Duration (s)</div>
                  <input value={configDuration} onChange={e => setConfigDuration(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleConfigureTransition} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Configure</button>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>preview_effect</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Effect Name</div>
                  <input value={effectName} onChange={e => setEffectName(e.target.value)} placeholder="e.g. CrossFade" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handlePreviewEffect} style={{
                  padding: '6px 14px', backgroundColor: '#3a2d3a', color: '#a29bfe',
                  border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Preview</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u2699\uFE0F'} Transition Configs <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({configs.length})</span>
            </div>
            {configs.map(config => (
              <div key={config.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #74b9ff',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{config.name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: '#1a2a3a', color: '#74b9ff', fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{config.type}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>
                  Duration: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{config.duration}s</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'events' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u25B6\uFE0F'} start_transition
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Config Name</div>
                  <input value={transitionConfig} onChange={e => setTransitionConfig(e.target.value)} placeholder="e.g. CrossFade" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleStartTransition} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Start</button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 160,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>update_progress</div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Progress (0-1)</div>
                    <input value={progressValue} onChange={e => setProgressValue(e.target.value)} style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <button onClick={handleUpdateProgress} style={{
                    padding: '6px 12px', backgroundColor: '#2d4a4a', color: '#00cec9',
                    border: '1px solid #3d5a5a', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                  }}>Update</button>
                </div>
              </div>

              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', flex: 1, minWidth: 160,
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>cancel_transition</div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Config</div>
                    <input value={cancelTarget} onChange={e => setCancelTarget(e.target.value)} placeholder="e.g. CrossFade" style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }} />
                  </div>
                  <button onClick={handleCancelTransition} style={{
                    padding: '6px 12px', backgroundColor: '#3a1a1a', color: '#ff6b6b',
                    border: '1px solid #5a2d2d', borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, fontWeight: 600,
                  }}>Cancel</button>
                </div>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u25B6\uFE0F'} get_active_transitions <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({activeTransitions.length})</span>
            </div>
            {activeTransitions.map(at => (
              <div key={at.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${at.status === 'running' ? '#6bcb77' : at.status === 'cancelled' ? '#ff6b6b' : '#fdcb6e'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{at.config_name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: at.status === 'running' ? '#1a3a1a' : at.status === 'cancelled' ? '#3a1a1a' : '#3a3a1a',
                    color: at.status === 'running' ? '#6bcb77' : at.status === 'cancelled' ? '#ff6b6b' : '#fdcb6e', fontWeight: 600,
                  }}>{at.status}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
                  Progress: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{(at.progress * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'sequences' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD17'} create_sequence
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={sequenceName} onChange={e => setSequenceName(e.target.value)} placeholder="e.g. IntroSequence" style={{
                    padding: '6px 10px', fontSize: 11, width: 200,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateSequence} style={{
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
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>add_step_to_sequence</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 2, minWidth: 140 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Config Name</div>
                  <input value={stepConfig} onChange={e => setStepConfig(e.target.value)} placeholder="e.g. CrossFade" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 70 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Delay (s)</div>
                  <input value={stepDelay} onChange={e => setStepDelay(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleAddStepToSequence} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Add Step</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD17'} Sequences <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({sequences.length})</span>
            </div>
            {sequences.map(seq => (
              <div key={seq.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{seq.name}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Steps: <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{seq.step_count}</span></span>
                </div>
              </div>
            ))}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginTop: 4 }}>
              {'\uD83D\uDDC4\uFE0F'} get_transition_history <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({history.length})</span>
            </div>
            {history.map(item => (
              <div key={item.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${item.status === 'completed' ? '#6bcb77' : '#fdcb6e'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: '#ccc' }}>{item.config_name}</span>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: item.status === 'completed' ? '#1a3a1a' : '#3a3a1a',
                    color: item.status === 'completed' ? '#6bcb77' : '#fdcb6e', fontWeight: 600,
                  }}>{item.status}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83C\uDFAC'} {configs.length} configs · {activeTransitions.length} active · {sequences.length} sequences · {history.length} history</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default SceneTransitionPanel;