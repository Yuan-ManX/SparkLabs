import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'entries' | 'search' | 'summaries';

interface JournalEntry {
  id: string;
  agent_id: string;
  title: string;
  content: string;
  entry_type: string;
  mood: string;
  tags: string[];
  created_at: number;
}

interface JournalSummary {
  id: string;
  agent_id: string;
  days: number;
  entry_count: number;
  summary_text: string;
  dominant_mood: string;
  generated_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const MOOD_COLORS: Record<string, string> = {
  positive: '#6bcb77',
  neutral: '#74b9ff',
  negative: '#ff6b6b',
  reflective: '#a29bfe',
  excited: '#fdcb6e',
};

const JournalSystemPanel: React.FC = () => {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [searchResults, setSearchResults] = useState<JournalEntry[]>([]);
  const [summaries, setSummaries] = useState<JournalSummary[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('entries');

  const [entryAgentId, setEntryAgentId] = useState('');
  const [entryTitle, setEntryTitle] = useState('');
  const [entryContent, setEntryContent] = useState('');
  const [entryType, setEntryType] = useState('reflection');
  const [entryMood, setEntryMood] = useState('neutral');
  const [entryTags, setEntryTags] = useState('');

  const [searchQuery, setSearchQuery] = useState('');
  const [searchAgentId, setSearchAgentId] = useState('');
  const [searchLimit, setSearchLimit] = useState('20');

  const [summaryAgentId, setSummaryAgentId] = useState('');
  const [summaryDays, setSummaryDays] = useState('7');

  const apiBase = API_ROOT + '/agent';

  const defaultEntries: JournalEntry[] = [
    { id: uid(), agent_id: 'agent-001', title: 'First Successful Code Generation', content: 'Today I successfully generated a complete React dashboard component. The user was pleased with the result and the code compiled on the first try.', entry_type: 'reflection', mood: 'positive', tags: ['coding', 'react', 'milestone'], created_at: Date.now() - 3600000 },
    { id: uid(), agent_id: 'agent-001', title: 'Debugging Session Notes', content: 'Encountered a tricky TypeScript generics error when refactoring the API client. Took about 15 minutes to resolve by simplifying the type constraints.', entry_type: 'debug_log', mood: 'neutral', tags: ['typescript', 'debugging'], created_at: Date.now() - 7200000 },
    { id: uid(), agent_id: 'agent-002', title: 'Learning New Pattern', content: 'Discovered a more elegant way to handle async state in React using useReducer. Will apply this pattern to future components.', entry_type: 'learning', mood: 'excited', tags: ['react', 'patterns', 'learning'], created_at: Date.now() - 10800000 },
    { id: uid(), agent_id: 'agent-001', title: 'Rate Limit Frustration', content: 'Hit the API rate limit three times today. Need to implement better request batching and caching strategies.', entry_type: 'reflection', mood: 'negative', tags: ['api', 'performance'], created_at: Date.now() - 14400000 },
  ];

  const defaultSummaries: JournalSummary[] = [
    {
      id: uid(), agent_id: 'agent-001', days: 7, entry_count: 12,
      summary_text: 'This week focused on React component development with TypeScript. Key achievements include a successful dashboard build and pattern discovery. Challenges involved API rate limiting and TypeScript generics.',
      dominant_mood: 'positive', generated_at: Date.now() - 86400000,
    },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/journal-system/stats`);
      const data = await res.json();
      if (data.entries) setEntries(data.entries);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setEntries(defaultEntries);
    setSummaries(defaultSummaries);
    fetchStats();
  }, [fetchStats]);

  const handleCreateEntry = async () => {
    if (!entryAgentId.trim() || !entryTitle.trim() || !entryContent.trim()) {
      showMessage('Agent ID, title, and content are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/journal-system/create-entry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: entryAgentId,
          title: entryTitle,
          content: entryContent,
          entry_type: entryType,
          mood: entryMood,
          tags: entryTags.split(',').map(t => t.trim()).filter(Boolean),
        }),
      });
      const newEntry: JournalEntry = {
        id: uid(),
        agent_id: entryAgentId,
        title: entryTitle,
        content: entryContent,
        entry_type: entryType,
        mood: entryMood,
        tags: entryTags.split(',').map(t => t.trim()).filter(Boolean),
        created_at: Date.now(),
      };
      setEntries(prev => [newEntry, ...prev]);
      setEntryTitle('');
      setEntryContent('');
      setEntryTags('');
      showMessage('Journal entry created', 'success');
    } catch {
      const newEntry: JournalEntry = {
        id: uid(),
        agent_id: entryAgentId,
        title: entryTitle,
        content: entryContent,
        entry_type: entryType,
        mood: entryMood,
        tags: entryTags.split(',').map(t => t.trim()).filter(Boolean),
        created_at: Date.now(),
      };
      setEntries(prev => [newEntry, ...prev]);
      setEntryTitle('');
      setEntryContent('');
      setEntryTags('');
      showMessage('Journal entry created (offline fallback)', 'info');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      showMessage('Search query is required', 'error');
      return;
    }
    try {
      const params = new URLSearchParams();
      params.set('query', searchQuery);
      if (searchAgentId) params.set('agent_id', searchAgentId);
      if (searchLimit) params.set('limit', searchLimit);
      const res = await fetch(`${apiBase}/journal-system/search?${params.toString()}`);
      const data = await res.json();
      if (data.entries) setSearchResults(data.entries);
      showMessage(`Search returned ${data.entries?.length || 0} entries`, 'success');
    } catch {
      const results = entries.filter(e =>
        e.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.content.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setSearchResults(results.slice(0, parseInt(searchLimit)));
      showMessage(`Search returned ${Math.min(results.length, parseInt(searchLimit))} entries (offline fallback)`, 'info');
    }
  };

  const handleSummarize = async () => {
    if (!summaryAgentId.trim()) {
      showMessage('Agent ID is required', 'error');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/journal-system/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: summaryAgentId, days: parseInt(summaryDays) }),
      });
      const data = await res.json();
      if (data) {
        setSummaries(prev => [data, ...prev]);
      }
      showMessage('Summary generated', 'success');
    } catch {
      const agentEntries = entries.filter(e => e.agent_id === summaryAgentId);
      const moods = agentEntries.map(e => e.mood);
      const dominantMood = moods.sort((a, b) => moods.filter(m => m === b).length - moods.filter(m => m === a).length)[0] || 'neutral';
      const summary: JournalSummary = {
        id: uid(),
        agent_id: summaryAgentId,
        days: parseInt(summaryDays),
        entry_count: agentEntries.length,
        summary_text: `Generated summary for agent ${summaryAgentId} covering the last ${summaryDays} days with ${agentEntries.length} entries.`,
        dominant_mood: dominantMood,
        generated_at: Date.now(),
      };
      setSummaries(prev => [summary, ...prev]);
      showMessage('Summary generated (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'entries', label: 'Entries', icon: '\uD83D\uDCD6', count: entries.length },
    { key: 'search', label: 'Search', icon: '\uD83D\uDD0D', count: searchResults.length },
    { key: 'summaries', label: 'Summaries', icon: '\uD83D\uDCDC', count: summaries.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCD6'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Journal System</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {entries.length} entries · {summaries.length} summaries
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
        {activeTab === 'entries' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCD6'} create-entry
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Agent ID</div>
                  <input value={entryAgentId} onChange={e => setEntryAgentId(e.target.value)} placeholder="e.g. agent-001" style={{
                    padding: '6px 10px', fontSize: 11, width: 100,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={entryType} onChange={e => setEntryType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="reflection">Reflection</option>
                    <option value="debug_log">Debug Log</option>
                    <option value="learning">Learning</option>
                    <option value="milestone">Milestone</option>
                    <option value="daily_log">Daily Log</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Mood</div>
                  <select value={entryMood} onChange={e => setEntryMood(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="positive">Positive</option>
                    <option value="neutral">Neutral</option>
                    <option value="negative">Negative</option>
                    <option value="reflective">Reflective</option>
                    <option value="excited">Excited</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Tags</div>
                  <input value={entryTags} onChange={e => setEntryTags(e.target.value)} placeholder="tag1,tag2" style={{
                    padding: '6px 10px', fontSize: 11, width: 130,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleCreateEntry} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Create</button>
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Title</div>
                <input value={entryTitle} onChange={e => setEntryTitle(e.target.value)} placeholder="Entry title..." style={{
                  padding: '6px 10px', fontSize: 11, width: '100%',
                  backgroundColor: '#141428', color: '#ccc',
                  border: '1px solid #333', borderRadius: 4, outline: 'none',
                }} />
              </div>
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Content</div>
                <textarea value={entryContent} onChange={e => setEntryContent(e.target.value)} placeholder="Write your journal entry..." rows={3} style={{
                  padding: '6px 10px', fontSize: 11, width: '100%', resize: 'vertical',
                  backgroundColor: '#141428', color: '#ccc',
                  border: '1px solid #333', borderRadius: 4, outline: 'none',
                  fontFamily: 'system-ui, sans-serif',
                }} />
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCD6'} Journal Entries <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({entries.length})</span>
            </div>
            {entries.map(entry => (
              <div key={entry.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${MOOD_COLORS[entry.mood] || '#888'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{entry.title}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: (MOOD_COLORS[entry.mood] || '#888') + '33',
                      color: MOOD_COLORS[entry.mood] || '#888', fontWeight: 600,
                    }}>{entry.mood}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{entry.agent_id}</span>
                </div>
                <div style={{ fontSize: 11, color: '#ccc', marginBottom: 6, lineHeight: 1.4 }}>
                  {entry.content.substring(0, 120)}{entry.content.length > 120 ? '...' : ''}
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10 }}>
                  <span style={{ color: '#888' }}>Type: <span style={{ color: '#74b9ff' }}>{entry.entry_type}</span></span>
                  <span style={{ color: '#888' }}>Tags: <span style={{ color: '#a29bfe' }}>{entry.tags.join(', ') || 'none'}</span></span>
                  <span style={{ color: '#666' }}>{formatTime(entry.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'search' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD0D'} search
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Query</div>
                  <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search entries..." style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Agent ID</div>
                  <input value={searchAgentId} onChange={e => setSearchAgentId(e.target.value)} placeholder="optional" style={{
                    padding: '6px 10px', fontSize: 11, width: 100,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Limit</div>
                  <input value={searchLimit} onChange={e => setSearchLimit(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleSearch} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Search</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD0D'} Search Results <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({searchResults.length})</span>
            </div>
            {searchResults.length > 0 ? searchResults.map(entry => (
              <div key={entry.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${MOOD_COLORS[entry.mood] || '#888'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{entry.title}</span>
                  <span style={{ fontSize: 10, color: '#888' }}>{entry.agent_id}</span>
                </div>
                <div style={{ fontSize: 10, color: '#ccc' }}>
                  {entry.content.substring(0, 80)}{entry.content.length > 80 ? '...' : ''}
                </div>
              </div>
            )) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD0D'}</span>
                Search for journal entries
              </div>
            )}
          </div>
        )}

        {activeTab === 'summaries' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCDC'} summarize
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Agent ID</div>
                  <input value={summaryAgentId} onChange={e => setSummaryAgentId(e.target.value)} placeholder="e.g. agent-001" style={{
                    padding: '6px 10px', fontSize: 11, width: 120,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Days</div>
                  <input value={summaryDays} onChange={e => setSummaryDays(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleSummarize} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Summarize</button>
              </div>
            </div>

            {summaries.map(summary => (
              <div key={summary.id} style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: `3px solid ${MOOD_COLORS[summary.dominant_mood] || '#e056a0'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 14, color: '#e056a0' }}>
                      {'\uD83D\uDCDC'} {summary.agent_id}
                    </span>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: (MOOD_COLORS[summary.dominant_mood] || '#888') + '33',
                      color: MOOD_COLORS[summary.dominant_mood] || '#888', fontWeight: 600,
                    }}>{summary.dominant_mood}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(summary.generated_at)}</span>
                </div>
                <div style={{ fontSize: 11, color: '#aaa', marginBottom: 6 }}>
                  {summary.days}d summary · {summary.entry_count} entries
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#141428', borderRadius: 4,
                  fontSize: 11, color: '#ccc', lineHeight: 1.5,
                }}>
                  {summary.summary_text}
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
        <span>{'\uD83D\uDCD6'} {entries.length} entries · {summaries.length} summaries</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default JournalSystemPanel;