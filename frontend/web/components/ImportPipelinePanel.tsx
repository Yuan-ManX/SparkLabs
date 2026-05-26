import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'imports' | 'profiles';

interface ImportTask {
  id: string;
  source: string;
  type: string;
  status: string;
  file_size: string;
}

interface ImportProfile {
  id: string;
  name: string;
  compression: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const ImportPipelinePanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('imports');
  const [loading, setLoading] = useState(false);

  const [importTasks, setImportTasks] = useState<ImportTask[]>([]);
  const [profiles, setProfiles] = useState<ImportProfile[]>([]);

  const [importSource, setImportSource] = useState('');
  const [importType, setImportType] = useState('fbx');
  const [profileName, setProfileName] = useState('');
  const [profileCompression, setProfileCompression] = useState('medium');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultImports: ImportTask[] = [
    { id: uid(), source: '/assets/hero_model.fbx', type: 'fbx', status: 'completed', file_size: '4.2 MB' },
    { id: uid(), source: '/assets/ground_texture.png', type: 'texture', status: 'completed', file_size: '2.1 MB' },
    { id: uid(), source: '/assets/theme.mp3', type: 'audio', status: 'pending', file_size: '8.7 MB' },
    { id: uid(), source: '/assets/enemy_anim.fbx', type: 'fbx', status: 'failed', file_size: '1.8 MB' },
  ];

  const defaultProfiles: ImportProfile[] = [
    { id: uid(), name: 'Textures (High)', compression: 'none' },
    { id: uid(), name: 'Models (Medium)', compression: 'medium' },
    { id: uid(), name: 'Audio (Low)', compression: 'high' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/import-pipeline/stats`);
      const data = await res.json();
      if (data.imports) setImportTasks(data.imports);
      if (data.profiles) setProfiles(data.profiles);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setImportTasks(defaultImports);
    setProfiles(defaultProfiles);
    fetchStats();
  }, [fetchStats]);

  const handleImportAsset = async () => {
    if (!importSource.trim()) { showMessage('Source path is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/import-pipeline/import-asset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: importSource, type: importType }),
      });
      const newTask: ImportTask = { id: uid(), source: importSource, type: importType, status: 'pending', file_size: '0 KB' };
      setImportTasks(prev => [...prev, newTask]);
      showMessage(`Import queued: ${importSource}`, 'success');
      setImportSource('');
    } catch {
      const newTask: ImportTask = { id: uid(), source: importSource, type: importType, status: 'pending', file_size: '0 KB' };
      setImportTasks(prev => [...prev, newTask]);
      showMessage(`Import queued (offline fallback)`, 'info');
      setImportSource('');
    }
    setLoading(false);
  };

  const handleCreateProfile = async () => {
    if (!profileName.trim()) { showMessage('Profile name is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/import-pipeline/create-profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: profileName, compression: profileCompression }),
      });
      const newProfile: ImportProfile = { id: uid(), name: profileName, compression: profileCompression };
      setProfiles(prev => [...prev, newProfile]);
      showMessage(`Profile "${profileName}" created`, 'success');
      setProfileName('');
      setProfileCompression('medium');
    } catch {
      const newProfile: ImportProfile = { id: uid(), name: profileName, compression: profileCompression };
      setProfiles(prev => [...prev, newProfile]);
      showMessage(`Profile created (offline fallback)`, 'info');
      setProfileName('');
      setProfileCompression('medium');
    }
    setLoading(false);
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'imports', label: 'Imports' },
    { key: 'profiles', label: 'Profiles' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  const statusBadgeStyle = (status: string) => {
    switch (status) {
      case 'completed': return { backgroundColor: '#1a3a1a', color: '#66bb6a' };
      case 'pending': return { backgroundColor: '#3a2a1a', color: '#ffa726' };
      case 'failed': return { backgroundColor: '#3a1a1a', color: '#ef5350' };
      case 'in_progress': return { backgroundColor: '#1a2a3a', color: '#4fc3f7' };
      default: return { backgroundColor: '#141428', color: '#888' };
    }
  };

  const typeColor = (type: string) => {
    switch (type) {
      case 'fbx': return '#4fc3f7';
      case 'texture': return '#66bb6a';
      case 'audio': return '#ffa726';
      default: return '#a29bfe';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCE5'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Import Pipeline</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{importTasks.length} imports · {profiles.length} profiles</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #4fc3f7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'imports' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Import Asset</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={importSource} onChange={e => setImportSource(e.target.value)} placeholder="Source path (/assets/file.fbx)" style={{ ...inputStyle, width: '100%' }} />
                <select value={importType} onChange={e => setImportType(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="fbx">FBX Model</option>
                  <option value="texture">Texture</option>
                  <option value="audio">Audio</option>
                  <option value="prefab">Prefab</option>
                </select>
                <button onClick={handleImportAsset} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Import</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Import Tasks ({importTasks.length})</div>
            {importTasks.map(task => (
              <div key={task.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11, color: '#ccc', marginBottom: 2, wordBreak: 'break-all' }}>{task.source}</div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: typeColor(task.type) }}>{task.type}</span>
                    <span style={{ fontSize: 9, color: '#666' }}>{task.file_size}</span>
                  </div>
                </div>
                <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, marginLeft: 8, whiteSpace: 'nowrap', ...statusBadgeStyle(task.status) }}>{task.status}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'profiles' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Create Import Profile</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={profileName} onChange={e => setProfileName(e.target.value)} placeholder="Profile name" style={{ ...inputStyle, width: '100%' }} />
                <select value={profileCompression} onChange={e => setProfileCompression(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="none">No Compression</option>
                  <option value="low">Low Compression</option>
                  <option value="medium">Medium Compression</option>
                  <option value="high">High Compression</option>
                </select>
                <button onClick={handleCreateProfile} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Profiles ({profiles.length})</div>
            {profiles.map(profile => (
              <div key={profile.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{profile.name}</span>
                <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: profile.compression === 'none' ? '#1a3a1a' : profile.compression === 'high' ? '#3a1a1a' : '#3a2a1a', color: profile.compression === 'none' ? '#66bb6a' : profile.compression === 'high' ? '#ef5350' : '#ffa726' }}>{profile.compression}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDCE5'} {importTasks.length} imports · {profiles.length} profiles</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default ImportPipelinePanel;