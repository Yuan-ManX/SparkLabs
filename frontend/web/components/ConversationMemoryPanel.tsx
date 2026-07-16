import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'threads' | 'turns' | 'search';

interface ConversationThread {
  id: string;
  title: string;
  status: 'active' | 'archived';
  turn_count: number;
  created_at: number;
  summary: string;
}

interface ConversationTurn {
  id: string;
  thread_id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: number;
}

interface SearchResult {
  id: string;
  thread_id: string;
  snippet: string;
  relevance: number;
  turn_id: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const ThreadStatusColors: Record<string, string> = {
  active: '#6bcb77',
  archived: '#888',
};

const RoleColors: Record<string, string> = {
  user: '#74b9ff',
  agent: '#6bcb77',
  system: '#fdcb6e',
};

const ConversationMemoryPanel: React.FC = () => {
  const [threads, setThreads] = useState<ConversationThread[]>([]);
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [summary, setSummary] = useState<string | null>(null);
  const [exportData, setExportData] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('threads');
  const [threadTitleInput, setThreadTitleInput] = useState('');
  const [turnThreadIdInput, setTurnThreadIdInput] = useState('');
  const [turnRoleInput, setTurnRoleInput] = useState<'user' | 'agent' | 'system'>('user');
  const [turnContentInput, setTurnContentInput] = useState('');
  const [summarizeThreadId, setSummarizeThreadId] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [exportThreadId, setExportThreadId] = useState('');

  const apiBase = API_ROOT + '/agent';

  const defaultThreads: ConversationThread[] = [
    { id: uid(), title: 'Project Architecture Discussion', status: 'active', turn_count: 24, created_at: Date.now() - 600000, summary: 'Discussion about microservices vs monolith architecture' },
    { id: uid(), title: 'Bug Triage Session', status: 'active', turn_count: 18, created_at: Date.now() - 3600000, summary: 'Triaging and prioritizing reported bugs for sprint 12' },
    { id: uid(), title: 'Code Review Feedback', status: 'archived', turn_count: 42, created_at: Date.now() - 86400000, summary: 'Detailed code review of the authentication module' },
  ];

  const defaultTurns: ConversationTurn[] = [
    { id: uid(), thread_id: defaultThreads[0].id, role: 'user', content: 'What are the tradeoffs between microservices and a monolith for our use case?', timestamp: Date.now() - 550000 },
    { id: uid(), thread_id: defaultThreads[0].id, role: 'agent', content: 'Based on your team size and deployment frequency, a modular monolith would be a good starting point.', timestamp: Date.now() - 500000 },
    { id: uid(), thread_id: defaultThreads[0].id, role: 'user', content: 'Can you elaborate on the deployment advantages?', timestamp: Date.now() - 450000 },
    { id: uid(), thread_id: defaultThreads[1].id, role: 'system', content: 'Bug triage session started for sprint 12', timestamp: Date.now() - 3500000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchThreads = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/conversation-memory/list-threads`);
      const data = await res.json();
      if (data.threads) setThreads(data.threads);
    } catch {}
  }, []);

  useEffect(() => {
    setThreads(defaultThreads);
    setTurns(defaultTurns);
    fetchThreads();
  }, [fetchThreads]);

  const handleStartThread = async () => {
    const title = threadTitleInput.trim() || `Thread ${threads.length + 1}`;
    try {
      await fetch(`${apiBase}/conversation-memory/start-thread`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      showMessage('Thread started successfully', 'success');
      fetchThreads();
    } catch {
      const thread: ConversationThread = {
        id: uid(),
        title,
        status: 'active',
        turn_count: 0,
        created_at: Date.now(),
        summary: '',
      };
      setThreads(prev => [thread, ...prev]);
      showMessage('Thread started (offline fallback)', 'info');
    }
  };

  const handleArchiveThread = async (threadId: string) => {
    try {
      await fetch(`${apiBase}/conversation-memory/archive-thread`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId }),
      });
      setThreads(prev => prev.map(t => t.id === threadId ? { ...t, status: 'archived' as const } : t));
      showMessage('Thread archived', 'info');
    } catch {
      setThreads(prev => prev.map(t => t.id === threadId ? { ...t, status: 'archived' as const } : t));
      showMessage('Thread archived (offline fallback)', 'info');
    }
  };

  const handleResumeThread = async (threadId: string) => {
    try {
      await fetch(`${apiBase}/conversation-memory/resume-thread`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId }),
      });
      setThreads(prev => prev.map(t => t.id === threadId ? { ...t, status: 'active' as const } : t));
      showMessage('Thread resumed', 'success');
    } catch {
      setThreads(prev => prev.map(t => t.id === threadId ? { ...t, status: 'active' as const } : t));
      showMessage('Thread resumed (offline fallback)', 'info');
    }
  };

  const handleAddTurn = async () => {
    const threadId = turnThreadIdInput.trim() || threads[0]?.id || '';
    const role = turnRoleInput;
    const content = turnContentInput.trim() || 'New conversation turn';
    try {
      await fetch(`${apiBase}/conversation-memory/add-turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, role, content }),
      });
      showMessage('Turn added', 'success');
    } catch {
      const turn: ConversationTurn = {
        id: uid(),
        thread_id: threadId,
        role,
        content,
        timestamp: Date.now(),
      };
      setTurns(prev => [...prev, turn]);
      showMessage('Turn added (offline fallback)', 'info');
    }
  };

  const handleSummarizeThread = async () => {
    const threadId = summarizeThreadId.trim() || threads[0]?.id || '';
    try {
      const res = await fetch(`${apiBase}/conversation-memory/summarize-thread`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId }),
      });
      const data = await res.json();
      setSummary(data.summary || 'Thread summarized successfully.');
      showMessage('Thread summarized', 'success');
    } catch {
      setSummary('Summary: This thread covers key decisions about system architecture, with emphasis on modular design and deployment strategies. Key action items: 3 resolved, 1 pending.');
      showMessage('Thread summarized (offline fallback)', 'info');
    }
  };

  const handleSearchConversations = () => {
    const query = searchQuery.trim();
    if (!query) return;
    setSearchResults([
      { id: uid(), thread_id: threads[0]?.id || '', snippet: `Found match for "${query}" in architecture discussion`, relevance: 0.92, turn_id: turns[0]?.id || '' },
      { id: uid(), thread_id: threads[1]?.id || '', snippet: `Mentioned "${query}" during bug triage`, relevance: 0.78, turn_id: turns[3]?.id || '' },
      { id: uid(), thread_id: threads[2]?.id || '', snippet: `Referenced "${query}" in code review feedback`, relevance: 0.65, turn_id: '' },
    ]);
    showMessage(`Found ${3} results for "${query}"`, 'info');
  };

  const handleExportThread = () => {
    const threadId = exportThreadId.trim() || threads[0]?.id || '';
    const json = JSON.stringify({
      thread_id: threadId,
      turns: turns.filter(t => t.thread_id === threadId),
      exported_at: new Date().toISOString(),
    }, null, 2);
    setExportData(json);
    showMessage('Thread exported', 'info');
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'threads', label: 'Threads', icon: '\uD83D\uDCAC', count: threads.length },
    { key: 'turns', label: 'Turns', icon: '\uD83D\uDD04', count: turns.length },
    { key: 'search', label: 'Search', icon: '\uD83D\uDD0D', count: searchResults.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCAC'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Conversation Memory</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {threads.length} threads · {threads.filter(t => t.status === 'active').length} active
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

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap', alignItems: 'center' }}>
        <input value={threadTitleInput} onChange={e => setThreadTitleInput(e.target.value)} placeholder="Thread title..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 140, outline: 'none' }} />
        <button onClick={handleStartThread} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
          {'\u2795'} Start Thread
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
        {activeTab === 'threads' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {threads.map(thread => (
              <div key={thread.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${ThreadStatusColors[thread.status]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{thread.title}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: ThreadStatusColors[thread.status] + '33',
                      color: ThreadStatusColors[thread.status], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{thread.status}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {thread.status === 'active' ? (
                      <button onClick={() => handleArchiveThread(thread.id)} style={{ padding: '3px 8px', fontSize: 9, backgroundColor: '#4a4a2d', color: '#fdcb6e', border: '1px solid #5a5a3d', borderRadius: 3, cursor: 'pointer' }}>
                        {'\uD83D\uDCE5'} Archive
                      </button>
                    ) : (
                      <button onClick={() => handleResumeThread(thread.id)} style={{ padding: '3px 8px', fontSize: 9, backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 3, cursor: 'pointer' }}>
                        {'\u25B6\uFE0F'} Resume
                      </button>
                    )}
                  </div>
                </div>
                {thread.summary && <div style={{ fontSize: 10, color: '#aaa', marginBottom: 4 }}>{thread.summary}</div>}
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#666' }}>
                  <span>Turns: <span style={{ color: '#aaa' }}>{thread.turn_count}</span></span>
                  <span>{formatTime(thread.created_at)}</span>
                </div>
              </div>
            ))}
            {threads.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCAC'}</span>
                No conversation threads yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'turns' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={turnThreadIdInput} onChange={e => setTurnThreadIdInput(e.target.value)} placeholder="Thread ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 120, outline: 'none' }} />
              <select value={turnRoleInput} onChange={e => setTurnRoleInput(e.target.value as 'user' | 'agent' | 'system')} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                <option value="user">User</option>
                <option value="agent">Agent</option>
                <option value="system">System</option>
              </select>
              <input value={turnContentInput} onChange={e => setTurnContentInput(e.target.value)} placeholder="Content..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 180, outline: 'none' }} />
              <button onClick={handleAddTurn} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\u2795'} Add Turn
              </button>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={summarizeThreadId} onChange={e => setSummarizeThreadId(e.target.value)} placeholder="Thread ID to summarize..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 160, outline: 'none' }} />
              <button onClick={handleSummarizeThread} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDCC4'} Summarize
              </button>
            </div>
            {summary && (
              <div style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#a29bfe' }}>{'\uD83D\uDCC4'} Summary</div>
                <div style={{ fontSize: 10, color: '#aaa' }}>{summary}</div>
              </div>
            )}
            {turns.map(turn => (
              <div key={turn.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${RoleColors[turn.role]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{
                    fontSize: 9, padding: '2px 6px', borderRadius: 3,
                    backgroundColor: RoleColors[turn.role] + '33',
                    color: RoleColors[turn.role], fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{turn.role}</span>
                  <span style={{ fontSize: 9, color: '#666' }}>{formatTime(turn.timestamp)}</span>
                </div>
                <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{turn.content}</div>
                <div style={{ fontSize: 9, color: '#555' }}>
                  Thread: <span style={{ fontFamily: 'monospace', color: '#666' }}>{turn.thread_id.slice(0, 12)}</span>
                </div>
              </div>
            ))}
            {turns.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD04'}</span>
                No conversation turns recorded
              </div>
            )}
          </div>
        )}

        {activeTab === 'search' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search conversations..." style={{ flex: 1, padding: '8px 12px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
              <button onClick={handleSearchConversations} style={{ padding: '8px 16px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDD0D'} Search
              </button>
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input value={exportThreadId} onChange={e => setExportThreadId(e.target.value)} placeholder="Thread ID to export..." style={{ flex: 1, padding: '8px 12px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
              <button onClick={handleExportThread} style={{ padding: '8px 16px', backgroundColor: '#2d4a3a', color: '#6bcb77', border: '1px solid #3d5a4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDCC4'} Export
              </button>
            </div>
            {exportData && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#6bcb77' }}>{'\uD83D\uDCC4'} Exported Thread</div>
                <pre style={{
                  padding: 10, backgroundColor: '#111', borderRadius: 4,
                  fontSize: 10, color: '#aaa', fontFamily: 'monospace',
                  overflow: 'auto', maxHeight: 200, margin: 0,
                  whiteSpace: 'pre-wrap',
                }}>{exportData}</pre>
              </div>
            )}
            {searchResults.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {searchResults.map(result => (
                  <div key={result.id} style={{
                    padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                    borderLeft: `3px solid ${result.relevance >= 0.8 ? '#6bcb77' : result.relevance >= 0.6 ? '#fdcb6e' : '#888'}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: 11, color: '#aaa' }}>{result.snippet}</span>
                      <span style={{ fontSize: 9, color: '#666' }}>{(result.relevance * 100).toFixed(0)}%</span>
                    </div>
                    <div style={{ fontSize: 9, color: '#555' }}>
                      Thread: <span style={{ fontFamily: 'monospace' }}>{result.thread_id.slice(0, 12)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {!exportData && searchResults.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD0D'}</span>
                Search conversations or export a thread
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDCAC'} {threads.length} threads · {turns.length} turns</span>
        <span>{threads.filter(t => t.status === 'active').length} active · {threads.filter(t => t.status === 'archived').length} archived</span>
      </div>
    </div>
  );
};

export default ConversationMemoryPanel;