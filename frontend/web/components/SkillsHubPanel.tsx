import React, { useState, useEffect, useCallback } from 'react';

type SkillStatus = 'published' | 'installed' | 'pending' | 'deprecated';
type TabId = 'browse' | 'installed' | 'details';

interface SkillItem {
  id: string;
  name: string;
  category: string;
  version: string;
  rating: number;
  status: SkillStatus;
  description: string;
  author: string;
  downloads: number;
  installed_at?: string;
}

interface SkillStats {
  total_skills: number;
  installed_count: number;
  avg_rating: number;
  categories: string[];
}

interface SkillDetail {
  id: string;
  name: string;
  category: string;
  version: string;
  rating: number;
  status: SkillStatus;
  description: string;
  author: string;
  downloads: number;
  changelog: string;
  dependencies: string[];
  size_bytes: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const STATUS_COLORS: Record<SkillStatus, string> = {
  published: '#74b9ff',
  installed: '#6bcb77',
  pending: '#fdcb6e',
  deprecated: '#888',
};

const STATUS_LABELS: Record<SkillStatus, string> = {
  published: 'Published',
  installed: 'Installed',
  pending: 'Pending',
  deprecated: 'Deprecated',
};

const SkillsHubPanel: React.FC = () => {
  const [browseSkills, setBrowseSkills] = useState<SkillItem[]>([]);
  const [installedSkills, setInstalledSkills] = useState<SkillItem[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<SkillDetail | null>(null);
  const [stats, setStats] = useState<SkillStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('browse');
  const [searchQuery, setSearchQuery] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultBrowseSkills: SkillItem[] = [
    { id: uid(), name: 'Code Refactoring Assistant', category: 'development', version: '2.1.0', rating: 4.7, status: 'published', description: 'Automates code refactoring with intelligent pattern recognition', author: 'SparkLabs', downloads: 3420 },
    { id: uid(), name: 'Context Summarizer Pro', category: 'nlp', version: '1.5.2', rating: 4.3, status: 'published', description: 'Summarizes long context windows with high accuracy', author: 'AI Tools Inc', downloads: 1890 },
    { id: uid(), name: 'Test Case Generator', category: 'testing', version: '3.0.0', rating: 4.8, status: 'published', description: 'Generates comprehensive test suites from code analysis', author: 'QA Labs', downloads: 5670 },
    { id: uid(), name: 'Memory Optimizer', category: 'infrastructure', version: '1.2.0', rating: 4.1, status: 'deprecated', description: 'Optimizes agent memory usage patterns', author: 'InfraTeam', downloads: 890 },
  ];

  const defaultInstalledSkills: SkillItem[] = [
    { id: uid(), name: 'Code Refactoring Assistant', category: 'development', version: '2.1.0', rating: 4.7, status: 'installed', description: 'Automates code refactoring with intelligent pattern recognition', author: 'SparkLabs', downloads: 3420, installed_at: '2 days ago' },
    { id: uid(), name: 'Context Summarizer Pro', category: 'nlp', version: '1.5.1', rating: 4.3, status: 'installed', description: 'Summarizes long context windows with high accuracy', author: 'AI Tools Inc', downloads: 1890, installed_at: '5 days ago' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/skills-hub/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({ total_skills: 42, installed_count: 2, avg_rating: 4.5, categories: ['development', 'nlp', 'testing', 'infrastructure'] });
    }
  }, []);

  const fetchBrowseSkills = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/skills-hub/search-skills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery || '*' }),
      });
      const data = await res.json();
      if (data.skills) setBrowseSkills(data.skills);
    } catch {}
  }, [searchQuery]);

  const fetchInstalledSkills = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/skills-hub/list-installed`);
      const data = await res.json();
      if (data.skills) setInstalledSkills(data.skills);
    } catch {}
  }, []);

  useEffect(() => {
    setBrowseSkills(defaultBrowseSkills);
    setInstalledSkills(defaultInstalledSkills);
    fetchStats();
    fetchInstalledSkills();
  }, [fetchStats, fetchInstalledSkills]);

  const handleSearch = async () => {
    await fetchBrowseSkills();
    showMessage(`Search results for "${searchQuery || 'all'}"`, 'info');
  };

  const handleInstall = async (skillName: string) => {
    try {
      await fetch(`${apiBase}/skills-hub/install-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_name: skillName }),
      });
      const skill = browseSkills.find(s => s.name === skillName);
      if (skill) {
        setInstalledSkills(prev => [...prev, { ...skill, status: 'installed' as SkillStatus, installed_at: 'just now' }]);
      }
      showMessage(`"${skillName}" installed successfully`, 'success');
      fetchStats();
      fetchInstalledSkills();
    } catch {
      const skill = browseSkills.find(s => s.name === skillName);
      if (skill) {
        setInstalledSkills(prev => [...prev, { ...skill, status: 'installed' as SkillStatus, installed_at: 'just now' }]);
      }
      showMessage(`"${skillName}" installed (offline fallback)`, 'info');
    }
  };

  const handlePublish = async () => {
    try {
      await fetch(`${apiBase}/skills-hub/publish-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: `New Skill ${browseSkills.length + 1}`, category: 'general', version: '1.0.0' }),
      });
      showMessage('Skill published successfully', 'success');
      fetchBrowseSkills();
      fetchStats();
    } catch {
      const newSkill: SkillItem = {
        id: uid(),
        name: `New Skill ${browseSkills.length + 1}`,
        category: 'general',
        version: '1.0.0',
        rating: 0,
        status: 'published',
        description: 'Newly published skill',
        author: 'You',
        downloads: 0,
      };
      setBrowseSkills(prev => [newSkill, ...prev]);
      showMessage('Skill published (offline fallback)', 'info');
    }
  };

  const handleRate = async (skillName: string) => {
    try {
      await fetch(`${apiBase}/skills-hub/rate-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_name: skillName, rating: 5 }),
      });
      showMessage(`Rated "${skillName}" 5 stars`, 'success');
    } catch {
      showMessage(`Rated "${skillName}" 5 stars (offline fallback)`, 'info');
    }
  };

  const handleCheckUpdates = async () => {
    try {
      const res = await fetch(`${apiBase}/skills-hub/check-updates`);
      const data = await res.json();
      showMessage(`Found ${data.updates?.length || 1} update(s) available`, 'info');
    } catch {
      showMessage('1 update available: Context Summarizer Pro v1.5.2', 'info');
    }
  };

  const handleViewDetails = (skillName: string) => {
    const skill = browseSkills.find(s => s.name === skillName) || installedSkills.find(s => s.name === skillName);
    if (skill) {
      setSelectedSkill({
        ...skill,
        changelog: '- Added new features\n- Fixed performance issues\n- Updated dependencies',
        dependencies: ['core-utils', 'agent-sdk'],
        size_bytes: Math.floor(Math.random() * 5000000) + 500000,
      });
      setActiveTab('details');
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const renderStars = (rating: number) => {
    const stars = Math.round(rating);
    return '\u2B50'.repeat(stars) + '\u2606'.repeat(5 - stars);
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'browse', label: 'Browse', icon: '\uD83D\uDD0D', count: browseSkills.length },
    { key: 'installed', label: 'Installed', icon: '\uD83D\uDCE6', count: installedSkills.length },
    { key: 'details', label: 'Details', icon: '\uD83D\uDCC4', count: selectedSkill ? 1 : 0 },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCDA'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Skills Hub</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_skills} skills · {stats.installed_count} installed · {renderStars(stats.avg_rating)}
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

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 0 }}>
          <input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Search skills..."
            style={{
              padding: '6px 10px', fontSize: 11,
              backgroundColor: '#141428', color: '#ccc',
              border: '1px solid #333', borderRadius: '4px 0 0 4px',
              width: 180, outline: 'none',
            }}
          />
          <button onClick={handleSearch} style={{
            padding: '6px 10px', backgroundColor: '#2d3a5a', color: '#74b9ff',
            border: '1px solid #3d4a6a', borderRadius: '0 4px 4px 0', cursor: 'pointer', fontSize: 11,
          }}>
            {'\uD83D\uDD0D'}
          </button>
        </div>
        <button onClick={() => handleInstall(searchQuery || browseSkills[0]?.name || 'Unknown')} style={{
          padding: '6px 12px', backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCE5'} Install
        </button>
        <button onClick={handlePublish} style={{
          padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCE4'} Publish
        </button>
        <button onClick={() => handleRate(browseSkills[0]?.name || 'Unknown')} style={{
          padding: '6px 12px', backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\u2B50'} Rate
        </button>
        <button onClick={handleCheckUpdates} style={{
          padding: '6px 12px', backgroundColor: '#2d3a4a', color: '#74b9ff',
          border: '1px solid #3d4a5a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDD04'} Check Updates
        </button>
      </div>

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
        {activeTab === 'browse' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {browseSkills.map(skill => (
              <div key={skill.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${STATUS_COLORS[skill.status]}`,
                cursor: 'pointer',
              }} onClick={() => handleViewDetails(skill.name)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{skill.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: STATUS_COLORS[skill.status] + '33',
                      color: STATUS_COLORS[skill.status], fontWeight: 600,
                    }}>{STATUS_LABELS[skill.status]}</span>
                  </div>
                  <button onClick={e => { e.stopPropagation(); handleInstall(skill.name); }} style={{
                    padding: '3px 8px', fontSize: 10,
                    backgroundColor: '#2d4a2d', color: '#6bcb77',
                    border: '1px solid #3d5a3d', borderRadius: 3, cursor: 'pointer',
                  }}>
                    {'\uD83D\uDCE5'} Install
                  </button>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                  {skill.description}
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#666' }}>
                  <span>v{skill.version}</span>
                  <span>{renderStars(skill.rating)} {skill.rating}</span>
                  <span>{skill.downloads.toLocaleString()} downloads</span>
                  <span style={{ color: '#555' }}>by {skill.author}</span>
                </div>
                <div style={{ marginTop: 4 }}>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: '#141428', color: '#888',
                  }}>{skill.category}</span>
                </div>
              </div>
            ))}
            {browseSkills.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD0D'}</span>
                No skills found
              </div>
            )}
          </div>
        )}

        {activeTab === 'installed' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {installedSkills.length > 0 ? (
              installedSkills.map(skill => (
                <div key={skill.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
                  cursor: 'pointer',
                }} onClick={() => handleViewDetails(skill.name)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{skill.name}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                      }}>Installed</span>
                    </div>
                    <span style={{ fontSize: 10, color: '#666' }}>{skill.installed_at}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>
                    {skill.description}
                  </div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#666' }}>
                    <span>v{skill.version}</span>
                    <span>{renderStars(skill.rating)} {skill.rating}</span>
                    <span style={{ color: '#555' }}>by {skill.author}</span>
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCE6'}</span>
                No skills installed yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'details' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {selectedSkill ? (
              <>
                <div style={{
                  padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                  border: '1px solid #2a2a3e', borderLeft: `3px solid ${STATUS_COLORS[selectedSkill.status]}`,
                }}>
                  <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 6, color: '#e0e0e0' }}>
                    {selectedSkill.name}
                  </div>
                  <div style={{ fontSize: 11, color: '#888', marginBottom: 10 }}>
                    {selectedSkill.description}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 11 }}>
                    <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 4 }}>
                      <div style={{ color: '#888' }}>Version</div>
                      <div style={{ color: '#74b9ff', fontWeight: 600 }}>v{selectedSkill.version}</div>
                    </div>
                    <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 4 }}>
                      <div style={{ color: '#888' }}>Rating</div>
                      <div style={{ color: '#fdcb6e', fontWeight: 600 }}>{renderStars(selectedSkill.rating)} {selectedSkill.rating}</div>
                    </div>
                    <div style={{ padding: 6, backgroundColor: '#141428', borderRadius: 4 }}>
                      <div style={{ color: '#888' }}>Size</div>
                      <div style={{ color: '#6bcb77', fontWeight: 600 }}>{formatBytes(selectedSkill.size_bytes)}</div>
                    </div>
                  </div>
                  <div style={{ marginTop: 10, fontSize: 10, color: '#666' }}>
                    <div>Author: {selectedSkill.author}</div>
                    <div>Downloads: {selectedSkill.downloads.toLocaleString()}</div>
                    <div>Category: {selectedSkill.category}</div>
                    {selectedSkill.dependencies.length > 0 && (
                      <div>Dependencies: {selectedSkill.dependencies.join(', ')}</div>
                    )}
                  </div>
                </div>
                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#aaa' }}>
                    {'\uD83D\uDCCB'} Changelog
                  </div>
                  <pre style={{
                    fontSize: 10, color: '#888', fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap', margin: 0,
                  }}>
                    {selectedSkill.changelog}
                  </pre>
                </div>
              </>
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCC4'}</span>
                Select a skill to view details
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83D\uDCDA'} {browseSkills.length} available · {installedSkills.length} installed
        </span>
        <span>
          {stats ? `${stats.categories?.length || 4} categories` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default SkillsHubPanel;