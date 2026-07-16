import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'stems' | 'playlists';

interface AudioStem {
  id: string;
  name: string;
  layer: string;
  volume: number;
}

interface Playlist {
  id: string;
  name: string;
  stems: string[];
  state: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const InteractiveAudioPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('stems');
  const [loading, setLoading] = useState(false);

  const [stems, setStems] = useState<AudioStem[]>([]);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);

  const [stemName, setStemName] = useState('');
  const [stemLayer, setStemLayer] = useState('melody');
  const [stemVolume, setStemVolume] = useState('0.8');

  const [playlistName, setPlaylistName] = useState('');
  const [playlistStems, setPlaylistStems] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultStems: AudioStem[] = [
    { id: uid(), name: 'piano_theme', layer: 'melody', volume: 0.85 },
    { id: uid(), name: 'bassline_groove', layer: 'bass', volume: 0.7 },
    { id: uid(), name: 'drum_loop_120', layer: 'percussion', volume: 0.75 },
    { id: uid(), name: 'ambient_pads', layer: 'ambient', volume: 0.4 },
  ];

  const defaultPlaylists: Playlist[] = [
    { id: uid(), name: 'Combat Layer', stems: ['drum_loop_120', 'bassline_groove'], state: 'playing' },
    { id: uid(), name: 'Exploration Ambience', stems: ['ambient_pads', 'piano_theme'], state: 'paused' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/interactive-audio/stats`);
      const data = await res.json();
      if (data.stems) setStems(data.stems);
      if (data.playlists) setPlaylists(data.playlists);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setStems(defaultStems);
    setPlaylists(defaultPlaylists);
    fetchStats();
  }, [fetchStats]);

  const handleCreateStem = async () => {
    if (!stemName.trim()) { showMessage('Stem name is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/interactive-audio/create-stem`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: stemName, layer: stemLayer, volume: parseFloat(stemVolume) }),
      });
      const newStem: AudioStem = { id: uid(), name: stemName, layer: stemLayer, volume: parseFloat(stemVolume) };
      setStems(prev => [...prev, newStem]);
      showMessage(`Stem "${stemName}" created`, 'success');
      setStemName('');
      setStemVolume('0.8');
    } catch {
      const newStem: AudioStem = { id: uid(), name: stemName, layer: stemLayer, volume: parseFloat(stemVolume) };
      setStems(prev => [...prev, newStem]);
      showMessage(`Stem created (offline fallback)`, 'info');
      setStemName('');
      setStemVolume('0.8');
    }
    setLoading(false);
  };

  const handleCreatePlaylist = async () => {
    if (!playlistName.trim()) { showMessage('Playlist name is required', 'error'); return; }
    setLoading(true);
    const stemNames = playlistStems.split(',').map(s => s.trim()).filter(Boolean);
    try {
      await fetch(`${apiBase}/interactive-audio/create-playlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: playlistName, stems: stemNames }),
      });
      const newPlaylist: Playlist = { id: uid(), name: playlistName, stems: stemNames, state: 'stopped' };
      setPlaylists(prev => [...prev, newPlaylist]);
      showMessage(`Playlist "${playlistName}" created`, 'success');
      setPlaylistName('');
      setPlaylistStems('');
    } catch {
      const newPlaylist: Playlist = { id: uid(), name: playlistName, stems: stemNames, state: 'stopped' };
      setPlaylists(prev => [...prev, newPlaylist]);
      showMessage(`Playlist created (offline fallback)`, 'info');
      setPlaylistName('');
      setPlaylistStems('');
    }
    setLoading(false);
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'stems', label: 'Stems' },
    { key: 'playlists', label: 'Playlists' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  const layerColor = (layer: string) => {
    switch (layer) {
      case 'melody': return '#4fc3f7';
      case 'bass': return '#a29bfe';
      case 'percussion': return '#ef5350';
      case 'ambient': return '#66bb6a';
      case 'sfx': return '#ffa726';
      default: return '#888';
    }
  };

  const stateColor = (state: string) => {
    switch (state) {
      case 'playing': return '#66bb6a';
      case 'paused': return '#ffa726';
      case 'stopped': return '#ef5350';
      default: return '#888';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDFB5'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Interactive Audio</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{stems.length} stems · {playlists.length} playlists</span>
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
        {activeTab === 'stems' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Create Audio Stem</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={stemName} onChange={e => setStemName(e.target.value)} placeholder="Stem name" style={{ ...inputStyle, width: '100%' }} />
                <select value={stemLayer} onChange={e => setStemLayer(e.target.value)} style={{ ...inputStyle, width: '100%' }}>
                  <option value="melody">melody</option>
                  <option value="bass">bass</option>
                  <option value="percussion">percussion</option>
                  <option value="ambient">ambient</option>
                  <option value="sfx">sfx</option>
                </select>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <input value={stemVolume} onChange={e => setStemVolume(e.target.value)} type="number" step="0.1" min="0" max="1" style={{ ...inputStyle, width: 80 }} />
                  <span style={{ fontSize: 10, color: '#888' }}>Volume (0-1)</span>
                </div>
                <button onClick={handleCreateStem} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Stems ({stems.length})</div>
            {stems.map(stem => (
              <div key={stem.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${layerColor(stem.layer)}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{stem.name}</span>
                  <span style={{ fontSize: 10, color: '#666', marginLeft: 8 }}>{stem.layer}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 60, height: 4, backgroundColor: '#111', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ width: `${stem.volume * 100}%`, height: '100%', backgroundColor: layerColor(stem.layer), borderRadius: 2 }} />
                  </div>
                  <span style={{ fontSize: 9, color: '#888', minWidth: 24, textAlign: 'right' }}>{(stem.volume * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'playlists' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Create Playlist</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={playlistName} onChange={e => setPlaylistName(e.target.value)} placeholder="Playlist name" style={{ ...inputStyle, width: '100%' }} />
                <input value={playlistStems} onChange={e => setPlaylistStems(e.target.value)} placeholder="Stems (comma-separated names)" style={{ ...inputStyle, width: '100%' }} />
                <button onClick={handleCreatePlaylist} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Create</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Playlists ({playlists.length})</div>
            {playlists.map(playlist => (
              <div key={playlist.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${stateColor(playlist.state)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{playlist.name}</span>
                  <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: playlist.state === 'playing' ? '#1a3a1a' : playlist.state === 'paused' ? '#3a2a1a' : '#3a1a1a', color: stateColor(playlist.state) }}>{playlist.state}</span>
                </div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {playlist.stems.map(stemName => {
                    const stem = stems.find(s => s.name === stemName);
                    return (
                      <span key={stemName} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: '#111', color: stem ? layerColor(stem.layer) : '#888', border: '1px solid #2a2a3e' }}>
                        {stemName}
                      </span>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83C\uDFB5'} {stems.length} stems · {playlists.length} playlists</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default InteractiveAudioPanel;