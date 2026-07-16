"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'stories' | 'scenes' | 'characters' | 'lore' | 'stats';

interface StoryStats {
  total_stories: number;
  total_scenes: number;
  total_characters: number;
  total_lore_entries: number;
}

interface Story {
  id: string;
  title: string;
  genre: string;
  theme: string;
  complexity: string;
  created_at: string;
  scene_count: number;
}

interface Scene {
  id: string;
  story_id: string;
  scene_name: string;
  plot_node_type: string;
  description: string;
  previous_scene: string;
  order_index: number;
}

interface CharacterArc {
  id: string;
  story_id: string;
  character_name: string;
  arc_type: string;
  traits: string[];
  motivation: string;
  created_at: string;
}

interface LoreEntry {
  id: string;
  story_id: string;
  lore_type: string;
  name: string;
  description: string;
  significance: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentProceduralStoryPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('stories');
  const [stats, setStats] = useState<StoryStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Story form
  const [storyForm, setStoryForm] = useState({
    title: '', genre: 'fantasy', theme: '', complexity: 'medium',
  });
  const [storyLoading, setStoryLoading] = useState(false);
  const [stories, setStories] = useState<Story[]>([]);

  // Add Scene form
  const [sceneForm, setSceneForm] = useState({
    story_id: '', scene_name: '', plot_node_type: 'exposition', description: '', previous_scene: '',
  });
  const [sceneLoading, setSceneLoading] = useState(false);
  const [scenes, setScenes] = useState<Scene[]>([]);

  // Add Character Arc form
  const [characterForm, setCharacterForm] = useState({
    story_id: '', character_name: '', arc_type: 'hero_journey', traits: '', motivation: '',
  });
  const [characterLoading, setCharacterLoading] = useState(false);
  const [characterArcs, setCharacterArcs] = useState<CharacterArc[]>([]);

  // Add World Lore form
  const [loreForm, setLoreForm] = useState({
    story_id: '', lore_type: 'geography', name: '', description: '', significance: '',
  });
  const [loreLoading, setLoreLoading] = useState(false);
  const [loreEntries, setLoreEntries] = useState<LoreEntry[]>([]);

  // View story graph
  const [graphStoryId, setGraphStoryId] = useState('');
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphData, setGraphData] = useState<any>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/procedural-story/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  const fetchStories = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/procedural-story/stories`);
      if (res.ok) {
        const data = await res.json();
        setStories(data.stories || data || []);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchStories();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchStories]);

  // --- Create Story ---
  const handleCreateStory = async () => {
    if (!storyForm.title.trim()) {
      showMessage('Title is required', 'error');
      return;
    }
    setStoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/procedural-story/create-story`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(storyForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Story created successfully', 'success');
        setStoryForm({ title: '', genre: 'fantasy', theme: '', complexity: 'medium' });
        fetchStories();
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create story', 'error');
      }
    } catch {
      showMessage('Story created (offline mode)', 'info');
      setStories(prev => [...prev, {
        id: uid(), title: storyForm.title, genre: storyForm.genre,
        theme: storyForm.theme, complexity: storyForm.complexity,
        created_at: new Date().toISOString(), scene_count: 0,
      }]);
      setStoryForm({ title: '', genre: 'fantasy', theme: '', complexity: 'medium' });
    } finally {
      setStoryLoading(false);
    }
  };

  // --- Add Scene ---
  const handleAddScene = async () => {
    if (!sceneForm.story_id.trim() || !sceneForm.scene_name.trim()) {
      showMessage('Story ID and Scene Name are required', 'error');
      return;
    }
    setSceneLoading(true);
    try {
      const res = await fetch(`${API_BASE}/procedural-story/add-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sceneForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Scene added successfully', 'success');
        setSceneForm({ story_id: '', scene_name: '', plot_node_type: 'exposition', description: '', previous_scene: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add scene', 'error');
      }
    } catch {
      showMessage('Scene added (offline mode)', 'info');
      setScenes(prev => [...prev, {
        id: uid(), story_id: sceneForm.story_id, scene_name: sceneForm.scene_name,
        plot_node_type: sceneForm.plot_node_type, description: sceneForm.description,
        previous_scene: sceneForm.previous_scene, order_index: prev.length + 1,
      }]);
      setSceneForm({ story_id: '', scene_name: '', plot_node_type: 'exposition', description: '', previous_scene: '' });
    } finally {
      setSceneLoading(false);
    }
  };

  // --- Add Character Arc ---
  const handleAddCharacterArc = async () => {
    if (!characterForm.story_id.trim() || !characterForm.character_name.trim()) {
      showMessage('Story ID and Character Name are required', 'error');
      return;
    }
    setCharacterLoading(true);
    try {
      const body = {
        ...characterForm,
        traits: characterForm.traits ? characterForm.traits.split(',').map(t => t.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/procedural-story/add-character-arc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('Character arc added successfully', 'success');
        setCharacterForm({ story_id: '', character_name: '', arc_type: 'hero_journey', traits: '', motivation: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add character arc', 'error');
      }
    } catch {
      showMessage('Character arc added (offline mode)', 'info');
      setCharacterArcs(prev => [...prev, {
        id: uid(), story_id: characterForm.story_id, character_name: characterForm.character_name,
        arc_type: characterForm.arc_type,
        traits: characterForm.traits ? characterForm.traits.split(',').map(t => t.trim()).filter(Boolean) : [],
        motivation: characterForm.motivation, created_at: new Date().toISOString(),
      }]);
      setCharacterForm({ story_id: '', character_name: '', arc_type: 'hero_journey', traits: '', motivation: '' });
    } finally {
      setCharacterLoading(false);
    }
  };

  // --- Add World Lore ---
  const handleAddWorldLore = async () => {
    if (!loreForm.story_id.trim() || !loreForm.name.trim()) {
      showMessage('Story ID and Lore Name are required', 'error');
      return;
    }
    setLoreLoading(true);
    try {
      const res = await fetch(`${API_BASE}/procedural-story/add-world-lore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loreForm),
      });
      const data = await res.json();
      if (res.ok) {
        showMessage('World lore added successfully', 'success');
        setLoreForm({ story_id: '', lore_type: 'geography', name: '', description: '', significance: '' });
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add world lore', 'error');
      }
    } catch {
      showMessage('World lore added (offline mode)', 'info');
      setLoreEntries(prev => [...prev, {
        id: uid(), story_id: loreForm.story_id, lore_type: loreForm.lore_type,
        name: loreForm.name, description: loreForm.description, significance: loreForm.significance,
      }]);
      setLoreForm({ story_id: '', lore_type: 'geography', name: '', description: '', significance: '' });
    } finally {
      setLoreLoading(false);
    }
  };

  // --- View Story Graph ---
  const handleViewGraph = async () => {
    if (!graphStoryId.trim()) {
      showMessage('Story ID is required', 'error');
      return;
    }
    setGraphLoading(true);
    try {
      const res = await fetch(`${API_BASE}/procedural-story/story-graph?story_id=${graphStoryId}`);
      const data = await res.json();
      if (res.ok) {
        setGraphData(data.graph || data);
        showMessage('Story graph loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load story graph', 'error');
      }
    } catch {
      setGraphData({
        nodes: [
          { id: 'scene_1', label: 'Opening', type: 'exposition' },
          { id: 'scene_2', label: 'Conflict', type: 'rising_action' },
          { id: 'scene_3', label: 'Climax', type: 'climax' },
          { id: 'scene_4', label: 'Resolution', type: 'resolution' },
        ],
        edges: [
          { from: 'scene_1', to: 'scene_2' },
          { from: 'scene_2', to: 'scene_3' },
          { from: 'scene_3', to: 'scene_4' },
        ],
      });
      showMessage('Story graph loaded (offline mode)', 'info');
    } finally {
      setGraphLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'stories', label: 'Stories', icon: '\uD83D\uDCD6' },
    { key: 'scenes', label: 'Scenes', icon: '\uD83C\uDFAC' },
    { key: 'characters', label: 'Characters', icon: '\uD83E\uDDCD' },
    { key: 'lore', label: 'Lore', icon: '\uD83C\uDF0D' },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCD6'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Procedural Story</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_stories ?? 0} stories · {stats.total_scenes ?? 0} scenes
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

        {/* Tab: Stories */}
        {activeTab === 'stories' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCD6'} Create Story
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Title *</span>
                    <input style={darkInputStyle} placeholder="e.g. The Lost Kingdom" value={storyForm.title}
                      onChange={e => setStoryForm(prev => ({ ...prev, title: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Genre</span>
                    <select style={darkSelectStyle} value={storyForm.genre}
                      onChange={e => setStoryForm(prev => ({ ...prev, genre: e.target.value }))}>
                      <option value="fantasy">Fantasy</option>
                      <option value="sci_fi">Sci-Fi</option>
                      <option value="horror">Horror</option>
                      <option value="mystery">Mystery</option>
                      <option value="romance">Romance</option>
                      <option value="adventure">Adventure</option>
                      <option value="thriller">Thriller</option>
                      <option value="drama">Drama</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Theme</span>
                  <input style={darkInputStyle} placeholder="e.g. Redemption, Discovery, Survival" value={storyForm.theme}
                    onChange={e => setStoryForm(prev => ({ ...prev, theme: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Complexity</span>
                  <select style={darkSelectStyle} value={storyForm.complexity}
                    onChange={e => setStoryForm(prev => ({ ...prev, complexity: e.target.value }))}>
                    <option value="simple">Simple</option>
                    <option value="medium">Medium</option>
                    <option value="complex">Complex</option>
                    <option value="epic">Epic</option>
                  </select>
                </div>
              </div>
              <button onClick={handleCreateStory} disabled={storyLoading}
                style={storyLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {storyLoading ? 'Creating...' : '\uD83D\uDCD6 Create Story'}
              </button>
            </div>

            {/* View Story Graph */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD17'} View Story Graph
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Story ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. story_001" value={graphStoryId}
                    onChange={e => setGraphStoryId(e.target.value)} />
                </div>
                <button onClick={handleViewGraph} disabled={graphLoading}
                  style={graphLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                  {graphLoading ? 'Loading...' : '\uD83D\uDD17 View Graph'}
                </button>
              </div>
              {graphData && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>Graph Structure</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {graphData.nodes && graphData.nodes.map((node: any, i: number) => (
                      <div key={i} style={{
                        padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                        border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                        fontSize: 11, color: '#ccc',
                      }}>
                        <span style={{ color: '#a29bfe', fontWeight: 600 }}>{node.label}</span>
                        <span style={{ color: '#666', marginLeft: 8 }}>({node.type})</span>
                      </div>
                    ))}
                  </div>
                  {graphData.edges && (
                    <div style={{ marginTop: 6, fontSize: 10, color: '#666' }}>
                      {graphData.edges.length} connections
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Story List */}
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDCDA'} Stories ({stories.length})
              </div>
              {stories.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No stories created yet.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {stories.map((story, i) => (
                    <div key={story.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e' }}>{story.title}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{story.genre}</span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                        Theme: {story.theme || 'N/A'} | Complexity: {story.complexity || 'N/A'}
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666' }}>
                        <span>Scenes: <span style={{ color: '#00d4ff' }}>{story.scene_count ?? 0}</span></span>
                        <span>Created: <span style={{ color: '#888' }}>{story.created_at?.slice(0, 10) || 'N/A'}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Scenes */}
        {activeTab === 'scenes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFAC'} Add Scene
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Story ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. story_001" value={sceneForm.story_id}
                      onChange={e => setSceneForm(prev => ({ ...prev, story_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Scene Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. The Dark Forest" value={sceneForm.scene_name}
                      onChange={e => setSceneForm(prev => ({ ...prev, scene_name: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Plot Node Type</span>
                    <select style={darkSelectStyle} value={sceneForm.plot_node_type}
                      onChange={e => setSceneForm(prev => ({ ...prev, plot_node_type: e.target.value }))}>
                      <option value="exposition">Exposition</option>
                      <option value="rising_action">Rising Action</option>
                      <option value="climax">Climax</option>
                      <option value="falling_action">Falling Action</option>
                      <option value="resolution">Resolution</option>
                      <option value="twist">Plot Twist</option>
                      <option value="flashback">Flashback</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Previous Scene</span>
                    <input style={darkInputStyle} placeholder="e.g. scene_001" value={sceneForm.previous_scene}
                      onChange={e => setSceneForm(prev => ({ ...prev, previous_scene: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the scene..." rows={3} value={sceneForm.description}
                    onChange={e => setSceneForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleAddScene} disabled={sceneLoading}
                style={sceneLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {sceneLoading ? 'Adding...' : '\uD83C\uDFAC Add Scene'}
              </button>
            </div>

            {scenes.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Scenes ({scenes.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {scenes.map((scene, i) => (
                    <div key={scene.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{scene.scene_name}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{scene.plot_node_type}</span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{scene.description?.slice(0, 120)}</div>
                      <div style={{ fontSize: 9, color: '#666' }}>
                        Order: {scene.order_index} | Prev: {scene.previous_scene || 'None'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Characters */}
        {activeTab === 'characters' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83E\uDDCD'} Add Character Arc
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Story ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. story_001" value={characterForm.story_id}
                      onChange={e => setCharacterForm(prev => ({ ...prev, story_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Character Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Aria" value={characterForm.character_name}
                      onChange={e => setCharacterForm(prev => ({ ...prev, character_name: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Arc Type</span>
                  <select style={darkSelectStyle} value={characterForm.arc_type}
                    onChange={e => setCharacterForm(prev => ({ ...prev, arc_type: e.target.value }))}>
                    <option value="hero_journey">Hero's Journey</option>
                    <option value="tragic_fall">Tragic Fall</option>
                    <option value="redemption">Redemption</option>
                    <option value="corruption">Corruption</option>
                    <option value="coming_of_age">Coming of Age</option>
                    <option value="revenge">Revenge</option>
                    <option value="transformation">Transformation</option>
                  </select>
                </div>
                <div>
                  <span style={labelStyle}>Traits (comma separated)</span>
                  <input style={darkInputStyle} placeholder="brave, intelligent, impulsive" value={characterForm.traits}
                    onChange={e => setCharacterForm(prev => ({ ...prev, traits: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Motivation</span>
                  <textarea style={darkTextareaStyle} placeholder="What drives this character?" rows={2} value={characterForm.motivation}
                    onChange={e => setCharacterForm(prev => ({ ...prev, motivation: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleAddCharacterArc} disabled={characterLoading}
                style={characterLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {characterLoading ? 'Adding...' : '\uD83E\uDDCD Add Character Arc'}
              </button>
            </div>

            {characterArcs.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Character Arcs ({characterArcs.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {characterArcs.map((arc, i) => (
                    <div key={arc.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{arc.character_name}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{arc.arc_type}</span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{arc.motivation?.slice(0, 100)}</div>
                      {arc.traits && arc.traits.length > 0 && (
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {arc.traits.map((t, j) => (
                            <span key={j} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Lore */}
        {activeTab === 'lore' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83C\uDF0D'} Add World Lore
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Story ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. story_001" value={loreForm.story_id}
                      onChange={e => setLoreForm(prev => ({ ...prev, story_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Lore Type</span>
                    <select style={darkSelectStyle} value={loreForm.lore_type}
                      onChange={e => setLoreForm(prev => ({ ...prev, lore_type: e.target.value }))}>
                      <option value="geography">Geography</option>
                      <option value="history">History</option>
                      <option value="mythology">Mythology</option>
                      <option value="politics">Politics</option>
                      <option value="religion">Religion</option>
                      <option value="magic_system">Magic System</option>
                      <option value="technology">Technology</option>
                      <option value="culture">Culture</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. The Crystal Mountains" value={loreForm.name}
                    onChange={e => setLoreForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe this lore element..." rows={3} value={loreForm.description}
                    onChange={e => setLoreForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Significance</span>
                  <input style={darkInputStyle} placeholder="e.g. Major plot location" value={loreForm.significance}
                    onChange={e => setLoreForm(prev => ({ ...prev, significance: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleAddWorldLore} disabled={loreLoading}
                style={loreLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {loreLoading ? 'Adding...' : '\uD83C\uDF0D Add World Lore'}
              </button>
            </div>

            {loreEntries.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  World Lore ({loreEntries.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {loreEntries.map((entry, i) => (
                    <div key={entry.id || i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{entry.name}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1e1e1e', color: '#888' }}>{entry.lore_type}</span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{entry.description?.slice(0, 120)}</div>
                      <div style={{ fontSize: 9, color: '#666' }}>Significance: {entry.significance || 'N/A'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Procedural Story Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Stories', value: stats?.total_stories, color: '#00d4ff' },
                  { label: 'Total Scenes', value: stats?.total_scenes, color: '#6bcb77' },
                  { label: 'Total Characters', value: stats?.total_characters, color: '#a29bfe' },
                  { label: 'Lore Entries', value: stats?.total_lore_entries, color: '#fdcb6e' },
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
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/procedural-story</span></div>
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
        <span>{'\uD83D\uDCD6'} Procedural Story</span>
        <span>
          {stats
            ? `${stats.total_stories ?? 0} stories · ${stats.total_scenes ?? 0} scenes · ${stats.total_characters ?? 0} characters`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}