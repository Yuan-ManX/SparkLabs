import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'effects' | 'chains' | 'profiles';

interface PostEffect {
  id: string;
  name: string;
  effect_type: string;
  enabled: boolean;
  quality: string;
  created_at: number;
}

interface EffectChain {
  id: string;
  name: string;
  effect_ids: string[];
  created_at: number;
}

interface PostProfile {
  id: string;
  name: string;
  description: string;
  chain_id: string;
  applied: boolean;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const EFFECT_TYPE_COLORS: Record<string, string> = {
  bloom: '#fdcb6e',
  dof: '#74b9ff',
  motion_blur: '#a29bfe',
  vignette: '#6bcb77',
  color_grading: '#e056a0',
  ssao: '#ff6b6b',
  tonemapping: '#00b894',
};

const PostProcessingPanel: React.FC = () => {
  const [effects, setEffects] = useState<PostEffect[]>([]);
  const [chains, setChains] = useState<EffectChain[]>([]);
  const [profiles, setProfiles] = useState<PostProfile[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('effects');

  const [effectName, setEffectName] = useState('');
  const [effectType, setEffectType] = useState('bloom');
  const [effectEnabled, setEffectEnabled] = useState(true);
  const [effectQuality, setEffectQuality] = useState('high');

  const [chainName, setChainName] = useState('');
  const [chainEffectIds, setChainEffectIds] = useState('');

  const [profileName, setProfileName] = useState('');
  const [profileDesc, setProfileDesc] = useState('');
  const [applyProfileId, setApplyProfileId] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultEffects: PostEffect[] = [
    { id: uid(), name: 'Bloom Glow', effect_type: 'bloom', enabled: true, quality: 'high', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Depth of Field', effect_type: 'dof', enabled: true, quality: 'medium', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Motion Blur', effect_type: 'motion_blur', enabled: false, quality: 'low', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Vignette Dark', effect_type: 'vignette', enabled: true, quality: 'high', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Color Grading Warm', effect_type: 'color_grading', enabled: true, quality: 'ultra', created_at: Date.now() - 259200000 },
  ];

  const defaultChains: EffectChain[] = [
    { id: uid(), name: 'Cinematic Look', effect_ids: ['eff-1', 'eff-2', 'eff-4', 'eff-5'], created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Performance Mode', effect_ids: ['eff-4'], created_at: Date.now() - 345600000 },
  ];

  const defaultProfiles: PostProfile[] = [
    { id: uid(), name: 'Cinematic Ultra', description: 'Full cinematic post-processing for cutscenes', chain_id: 'chain-1', applied: false, created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Gameplay Balanced', description: 'Balanced effects for gameplay', chain_id: 'chain-2', applied: true, created_at: Date.now() - 172800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/post-processing/stats`);
      const data = await res.json();
      if (data.effects) setEffects(data.effects);
      if (data.chains) setChains(data.chains);
      if (data.profiles) setProfiles(data.profiles);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setEffects(defaultEffects);
    setChains(defaultChains);
    setProfiles(defaultProfiles);
    fetchStats();
  }, [fetchStats]);

  const handleAddEffect = async () => {
    if (!effectName.trim()) {
      showMessage('Effect name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/post-processing/add-effect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: effectName, effect_type: effectType, enabled: effectEnabled, quality: effectQuality }),
      });
      const newEffect: PostEffect = {
        id: uid(), name: effectName, effect_type: effectType, enabled: effectEnabled, quality: effectQuality, created_at: Date.now(),
      };
      setEffects(prev => [...prev, newEffect]);
      setEffectName('');
      showMessage(`Effect "${effectName}" added`, 'success');
    } catch {
      const newEffect: PostEffect = {
        id: uid(), name: effectName, effect_type: effectType, enabled: effectEnabled, quality: effectQuality, created_at: Date.now(),
      };
      setEffects(prev => [...prev, newEffect]);
      setEffectName('');
      showMessage(`Effect "${effectName}" added (offline fallback)`, 'info');
    }
  };

  const handleCreateChain = async () => {
    if (!chainName.trim()) {
      showMessage('Chain name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/post-processing/create-chain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: chainName }),
      });
      const newChain: EffectChain = {
        id: uid(),
        name: chainName,
        effect_ids: chainEffectIds.split(',').map(s => s.trim()).filter(Boolean),
        created_at: Date.now(),
      };
      setChains(prev => [...prev, newChain]);
      setChainName('');
      setChainEffectIds('');
      showMessage(`Chain "${chainName}" created`, 'success');
    } catch {
      const newChain: EffectChain = {
        id: uid(),
        name: chainName,
        effect_ids: chainEffectIds.split(',').map(s => s.trim()).filter(Boolean),
        created_at: Date.now(),
      };
      setChains(prev => [...prev, newChain]);
      setChainName('');
      setChainEffectIds('');
      showMessage(`Chain "${chainName}" created (offline fallback)`, 'info');
    }
  };

  const handleCreateProfile = async () => {
    if (!profileName.trim()) {
      showMessage('Profile name is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/post-processing/create-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: profileName, description: profileDesc }),
      });
      const newProfile: PostProfile = {
        id: uid(),
        name: profileName,
        description: profileDesc,
        chain_id: chains[0]?.id || '',
        applied: false,
        created_at: Date.now(),
      };
      setProfiles(prev => [...prev, newProfile]);
      setProfileName('');
      setProfileDesc('');
      showMessage(`Profile "${profileName}" created`, 'success');
    } catch {
      const newProfile: PostProfile = {
        id: uid(),
        name: profileName,
        description: profileDesc,
        chain_id: chains[0]?.id || '',
        applied: false,
        created_at: Date.now(),
      };
      setProfiles(prev => [...prev, newProfile]);
      setProfileName('');
      setProfileDesc('');
      showMessage(`Profile "${profileName}" created (offline fallback)`, 'info');
    }
  };

  const handleApplyProfile = async () => {
    if (!applyProfileId.trim()) {
      showMessage('Profile ID is required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/post-processing/apply-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: applyProfileId }),
      });
      setProfiles(prev => prev.map(p => ({
        ...p,
        applied: p.id === applyProfileId,
      })));
      const profile = profiles.find(p => p.id === applyProfileId);
      showMessage(`Profile "${profile?.name || applyProfileId}" applied`, 'success');
    } catch {
      setProfiles(prev => prev.map(p => ({
        ...p,
        applied: p.id === applyProfileId,
      })));
      const profile = profiles.find(p => p.id === applyProfileId);
      showMessage(`Profile "${profile?.name || applyProfileId}" applied (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'effects', label: 'Effects', icon: '\u2728', count: effects.length },
    { key: 'chains', label: 'Chains', icon: '\uD83D\uDD17', count: chains.length },
    { key: 'profiles', label: 'Profiles', icon: '\uD83D\uDCBE', count: profiles.length },
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
          <span style={{ fontSize: 18 }}>{'\u2728'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Post Processing</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {effects.length} effects · {chains.length} chains · {profiles.length} profiles
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
        {activeTab === 'effects' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u2728'} add-effect
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={effectName} onChange={e => setEffectName(e.target.value)} placeholder="e.g. Bloom Glow" style={{
                    padding: '6px 10px', fontSize: 11, width: 130,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={effectType} onChange={e => setEffectType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="bloom">Bloom</option>
                    <option value="dof">Depth of Field</option>
                    <option value="motion_blur">Motion Blur</option>
                    <option value="vignette">Vignette</option>
                    <option value="color_grading">Color Grading</option>
                    <option value="ssao">SSAO</option>
                    <option value="tonemapping">Tonemapping</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Quality</div>
                  <select value={effectQuality} onChange={e => setEffectQuality(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="ultra">Ultra</option>
                  </select>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
                  <label style={{ fontSize: 10, color: '#888' }}>
                    <input type="checkbox" checked={effectEnabled} onChange={e => setEffectEnabled(e.target.checked)} style={{ marginRight: 3 }} />
                    Enabled
                  </label>
                </div>
                <button onClick={handleAddEffect} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Add</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u2728'} Post Effects <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({effects.length})</span>
            </div>
            {effects.map(eff => (
              <div key={eff.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${EFFECT_TYPE_COLORS[eff.effect_type] || '#888'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{eff.name}</span>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: (EFFECT_TYPE_COLORS[eff.effect_type] || '#888') + '33',
                      color: EFFECT_TYPE_COLORS[eff.effect_type] || '#888', fontWeight: 600,
                    }}>{eff.effect_type}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: eff.enabled ? '#1a3a1a' : '#3a1a1a',
                      color: eff.enabled ? '#6bcb77' : '#ff6b6b', fontWeight: 600,
                    }}>{eff.enabled ? 'ON' : 'OFF'}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Quality: <span style={{ color: '#fdcb6e', fontWeight: 600, textTransform: 'uppercase' }}>{eff.quality}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'chains' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD17'} create-chain
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={chainName} onChange={e => setChainName(e.target.value)} placeholder="e.g. Cinematic Look" style={{
                    padding: '6px 10px', fontSize: 11, width: 150,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Effect IDs (comma-separated)</div>
                  <input value={chainEffectIds} onChange={e => setChainEffectIds(e.target.value)} placeholder="eff-1, eff-2, eff-3" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateChain} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD17'} Effect Chains <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({chains.length})</span>
            </div>
            {chains.map(chain => (
              <div key={chain.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#ccc', marginBottom: 6 }}>{chain.name}</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {chain.effect_ids.map(eid => {
                    const eff = effects.find(e => e.id === eid);
                    return (
                      <span key={eid} style={{
                        fontSize: 9, padding: '2px 6px', borderRadius: 3,
                        backgroundColor: '#111',
                        color: eff ? EFFECT_TYPE_COLORS[eff.effect_type] || '#aaa' : '#888',
                      }}>
                        {eff?.name || eid}
                      </span>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'profiles' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCBE'} create-profile
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input value={profileName} onChange={e => setProfileName(e.target.value)} placeholder="e.g. Cinematic Ultra" style={{
                    padding: '6px 10px', fontSize: 11, width: 140,
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Description</div>
                  <input value={profileDesc} onChange={e => setProfileDesc(e.target.value)} placeholder="Profile description..." style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateProfile} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
            </div>

            <div style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>apply-profile</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Profile ID</div>
                  <input value={applyProfileId} onChange={e => setApplyProfileId(e.target.value)} placeholder="Select profile" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#111', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleApplyProfile} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Apply</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCBE'} Profiles <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({profiles.length})</span>
            </div>
            {profiles.map(profile => (
              <div key={profile.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${profile.applied ? '#6bcb77' : '#e056a0'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{profile.name}</span>
                    {profile.applied && (
                      <span style={{
                        fontSize: 9, padding: '2px 8px', borderRadius: 3,
                        backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                      }}>ACTIVE</span>
                    )}
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{profile.description}</div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#888' }}>
                  <span>Chain: <span style={{ color: '#a29bfe' }}>{profile.chain_id}</span></span>
                  <span>Created: <span style={{ color: '#aaa' }}>{formatTime(profile.created_at)}</span></span>
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
        <span>{'\u2728'} {effects.length} effects · {chains.length} chains · {profiles.length} profiles</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default PostProcessingPanel;