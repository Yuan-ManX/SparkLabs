import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'extensions' | 'capabilities';

interface Extension {
  id: string;
  name: string;
  type: string;
  version: string;
  status: string;
}

interface Capability {
  id: string;
  name: string;
  scope: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const ExtensionSdkPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('extensions');
  const [loading, setLoading] = useState(false);

  const [extensions, setExtensions] = useState<Extension[]>([]);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [searchResults, setSearchResults] = useState<Extension[]>([]);

  const [extName, setExtName] = useState('');
  const [extType, setExtType] = useState('plugin');
  const [extVersion, setExtVersion] = useState('1.0.0');
  const [searchQuery, setSearchQuery] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultExtensions: Extension[] = [
    { id: uid(), name: 'markdown_previewer', type: 'plugin', version: '2.1.0', status: 'active' },
    { id: uid(), name: 'sql_formatter', type: 'tool', version: '1.3.2', status: 'active' },
    { id: uid(), name: 'theme_switcher', type: 'theme', version: '0.9.0', status: 'disabled' },
    { id: uid(), name: 'git_blame_viewer', type: 'plugin', version: '3.0.1', status: 'active' },
  ];

  const defaultCapabilities: Capability[] = [
    { id: uid(), name: 'file_system_access', scope: 'workspace' },
    { id: uid(), name: 'network_requests', scope: 'global' },
    { id: uid(), name: 'clipboard_read', scope: 'document' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/extension-sdk/stats`);
      const data = await res.json();
      if (data.extensions) setExtensions(data.extensions);
      if (data.capabilities) setCapabilities(data.capabilities);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setExtensions(defaultExtensions);
    setCapabilities(defaultCapabilities);
    fetchStats();
  }, [fetchStats]);

  const handleRegisterExtension = async () => {
    if (!extName.trim()) { showMessage('Extension name is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/extension-sdk/register-extension`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: extName, type: extType, version: extVersion }),
      });
      const newExt: Extension = { id: uid(), name: extName, type: extType, version: extVersion, status: 'active' };
      setExtensions(prev => [...prev, newExt]);
      showMessage(`Extension "${extName}" registered`, 'success');
      setExtName('');
      setExtVersion('1.0.0');
    } catch {
      const newExt: Extension = { id: uid(), name: extName, type: extType, version: extVersion, status: 'active' };
      setExtensions(prev => [...prev, newExt]);
      showMessage(`Extension registered (offline fallback)`, 'info');
      setExtName('');
      setExtVersion('1.0.0');
    }
    setLoading(false);
  };

  const handleSearchExtensions = async () => {
    if (!searchQuery.trim()) { showMessage('Search query is required', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/extension-sdk/search-extensions?q=${encodeURIComponent(searchQuery)}`);
      const data = await res.json();
      if (data.extensions) setSearchResults(data.extensions);
      showMessage(`Found ${data.extensions?.length || 0} extensions`, 'success');
    } catch {
      const filtered = extensions.filter(e => e.name.toLowerCase().includes(searchQuery.toLowerCase()));
      setSearchResults(filtered);
      showMessage(`Found ${filtered.length} extensions (offline fallback)`, 'info');
    }
    setLoading(false);
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'extensions', label: 'Extensions' },
    { key: 'capabilities', label: 'Capabilities' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  const statusBadge = (status: string) => {
    const color = status === 'active' ? '#66bb6a' : status === 'disabled' ? '#ef5350' : '#ffa726';
    const bg = status === 'active' ? '#1a3a1a' : status === 'disabled' ? '#3a1a1a' : '#3a2a1a';
    return { backgroundColor: bg, color };
  };

  const typeColor = (type: string) => {
    switch (type) {
      case 'plugin': return '#a29bfe';
      case 'tool': return '#4fc3f7';
      case 'theme': return '#ffa726';
      default: return '#aaa';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDE9'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Extension SDK</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{extensions.length} extensions · {capabilities.length} capabilities</span>
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
        {activeTab === 'extensions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Register Extension</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={extName} onChange={e => setExtName(e.target.value)} placeholder="Extension name" style={{ ...inputStyle, width: '100%' }} />
                <div style={{ display: 'flex', gap: 6 }}>
                  <select value={extType} onChange={e => setExtType(e.target.value)} style={{ ...inputStyle, flex: 1 }}>
                    <option value="plugin">plugin</option>
                    <option value="tool">tool</option>
                    <option value="theme">theme</option>
                    <option value="language">language</option>
                  </select>
                  <input value={extVersion} onChange={e => setExtVersion(e.target.value)} placeholder="Version" style={{ ...inputStyle, flex: 1 }} />
                </div>
                <button onClick={handleRegisterExtension} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Register</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Search Extensions</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search by name" style={{ ...inputStyle, flex: 1 }} />
                <button onClick={handleSearchExtensions} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Search</button>
              </div>
            </div>

            {searchResults.length > 0 && (
              <>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Search Results ({searchResults.length})</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
                  {searchResults.map(ext => (
                    <div key={ext.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${typeColor(ext.type)}` }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#ccc', marginBottom: 4 }}>{ext.name}</div>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: typeColor(ext.type) }}>{ext.type}</span>
                        <span style={{ fontSize: 9, color: '#666' }}>v{ext.version}</span>
                      </div>
                      <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, ...statusBadge(ext.status) }}>{ext.status}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Installed Extensions ({extensions.length})</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
              {extensions.map(ext => (
                <div key={ext.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${typeColor(ext.type)}` }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: '#ccc', marginBottom: 4 }}>{ext.name}</div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginBottom: 4 }}>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: typeColor(ext.type) }}>{ext.type}</span>
                    <span style={{ fontSize: 9, color: '#666' }}>v{ext.version}</span>
                  </div>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, ...statusBadge(ext.status) }}>{ext.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'capabilities' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Available Capabilities ({capabilities.length})</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
              {capabilities.map(cap => (
                <div key={cap.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                  <div style={{ fontSize: 12, color: '#ccc', marginBottom: 4, fontFamily: 'monospace' }}>{cap.name}</div>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#111', color: cap.scope === 'global' ? '#ef5350' : cap.scope === 'workspace' ? '#ffa726' : '#4fc3f7' }}>{cap.scope}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83E\uDDE9'} {extensions.length} extensions · {capabilities.length} capabilities</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default ExtensionSdkPanel;