"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'overview' | 'store-core' | 'store-session' | 'search' | 'consolidate' | 'context';

interface LayerStats {
  total_core_memories: number;
  total_session_memories: number;
  total_memories: number;
  last_consolidation: string | null;
  consolidation_count: number;
}

interface MemoryEntry {
  id: string;
  content: string;
  category: string;
  priority: string;
  metadata: Record<string, unknown>;
  source: string;
  layer: 'core' | 'session';
  created_at: string;
}

interface SearchResult {
  entry: MemoryEntry;
  relevance: number;
  snippet: string;
  layer: string;
}

interface ContextResult {
  tokens_used: number;
  max_tokens: number;
  entries: MemoryEntry[];
  context_text: string;
}

interface ConsolidateResult {
  consolidated_from: number;
  consolidated_to: number;
  removed: number;
  timestamp: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const CATEGORIES = ['general', 'fact', 'preference', 'instruction', 'pattern', 'insight'];
const PRIORITIES = ['critical', 'high', 'medium', 'low', 'transient'];
const SOURCES = ['user', 'system', 'inference', 'observation', 'external'];

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#ff6b6b',
  high: '#e17055',
  medium: '#fdcb6e',
  low: '#6bcb77',
  transient: '#888',
};

const CATEGORY_COLORS: Record<string, string> = {
  general: '#a29bfe',
  fact: '#74b9ff',
  preference: '#fdcb6e',
  instruction: '#00b894',
  pattern: '#e17055',
  insight: '#6c5ce7',
};

const LAYER_COLORS: Record<string, string> = {
  core: '#6c5ce7',
  session: '#00b894',
};

const AgentLayeredMemoryPanel: React.FC = () => {
  const [stats, setStats] = useState<LayerStats | null>(null);
  const [coreMemories, setCoreMemories] = useState<MemoryEntry[]>([]);
  const [sessionMemories, setSessionMemories] = useState<MemoryEntry[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [contextResult, setContextResult] = useState<ContextResult | null>(null);
  const [consolidateResult, setConsolidateResult] = useState<ConsolidateResult | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  // Store form state
  const [storeContent, setStoreContent] = useState('');
  const [storeCategory, setStoreCategory] = useState('general');
  const [storePriority, setStorePriority] = useState('medium');
  const [storeMetadata, setStoreMetadata] = useState('');
  const [storeSource, setStoreSource] = useState('user');

  // Search form state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLayers, setSearchLayers] = useState('');
  const [searchLimit, setSearchLimit] = useState('20');

  // Context form state
  const [contextMaxTokens, setContextMaxTokens] = useState('2000');

  const apiBase = API_ROOT + '/agent';

  const defaultStats: LayerStats = {
    total_core_memories: 12,
    total_session_memories: 34,
    total_memories: 46,
    last_consolidation: '2h ago',
    consolidation_count: 5,
  };

  const defaultCoreMemories: MemoryEntry[] = [
    { id: uid(), content: 'User prefers TypeScript with strict mode', category: 'preference', priority: 'high', metadata: { language: 'typescript' }, source: 'inference', layer: 'core', created_at: '1d ago' },
    { id: uid(), content: 'Primary project: SparkLabs game engine', category: 'fact', priority: 'critical', metadata: { project: 'sparklabs' }, source: 'user', layer: 'core', created_at: '3d ago' },
    { id: uid(), content: 'Deployment uses Docker + Kubernetes', category: 'fact', priority: 'medium', metadata: { infra: 'docker' }, source: 'observation', layer: 'core', created_at: '5d ago' },
  ];

  const defaultSessionMemories: MemoryEntry[] = [
    { id: uid(), content: 'Debugging WebSocket race condition in handler', category: 'pattern', priority: 'high', metadata: { bug: 'race-condition' }, source: 'observation', layer: 'session', created_at: '10m ago' },
    { id: uid(), content: 'Refactored inventory module to use generics', category: 'insight', priority: 'medium', metadata: { module: 'inventory' }, source: 'user', layer: 'session', created_at: '30m ago' },
    { id: uid(), content: 'API rate limiting strategy discussed', category: 'general', priority: 'low', metadata: { topic: 'rate-limiting' }, source: 'user', layer: 'session', created_at: '1h ago' },
  ];

  const defaultSearchResults: SearchResult[] = [
    { entry: defaultCoreMemories[0], relevance: 0.92, snippet: 'User has consistently preferred TypeScript with strict mode enabled across all projects.', layer: 'core' },
    { entry: defaultSessionMemories[1], relevance: 0.78, snippet: 'The inventory module was refactored to use generic types for better type safety.', layer: 'session' },
    { entry: defaultCoreMemories[1], relevance: 0.65, snippet: 'SparkLabs is the primary game engine project under active development.', layer: 'core' },
  ];

  const defaultContext: ContextResult = {
    tokens_used: 856,
    max_tokens: 2000,
    entries: [...defaultCoreMemories, ...defaultSessionMemories.slice(0, 2)],
    context_text: 'User prefers TypeScript with strict mode. Primary project: SparkLabs game engine. Deployment uses Docker + Kubernetes. Debugging WebSocket race condition...',
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/layered-memory/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats(defaultStats);
    }
  }, []);

  const fetchContext = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/layered-memory/context?max_tokens=${contextMaxTokens}`);
      const data = await res.json();
      setContextResult(data);
    } catch {
      setContextResult(defaultContext);
    }
  }, [contextMaxTokens]);

  useEffect(() => {
    setCoreMemories(defaultCoreMemories);
    setSessionMemories(defaultSessionMemories);
    setSearchResults(defaultSearchResults);
    fetchStats();
    fetchContext();
  }, [fetchStats, fetchContext]);

  const handleStoreCore = async () => {
    if (!storeContent.trim()) { showMessage('Content is required', 'error'); return; }
    try {
      const metadata = storeMetadata ? JSON.parse(storeMetadata) : {};
      const res = await fetch(`${apiBase}/layered-memory/store-core`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: storeContent,
          category: storeCategory,
          priority: storePriority,
          metadata,
          source: storeSource,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const entry: MemoryEntry = {
        id: data.id || uid(),
        content: data.content || storeContent,
        category: data.category || storeCategory,
        priority: data.priority || storePriority,
        metadata: data.metadata || metadata,
        source: data.source || storeSource,
        layer: 'core',
        created_at: 'just now',
      };
      setCoreMemories(prev => [entry, ...prev]);
      setStoreContent('');
      setStoreMetadata('');
      showMessage('Core memory stored', 'success');
      fetchStats();
    } catch {
      const entry: MemoryEntry = {
        id: uid(),
        content: storeContent,
        category: storeCategory,
        priority: storePriority,
        metadata: storeMetadata ? JSON.parse(storeMetadata) : {},
        source: storeSource,
        layer: 'core',
        created_at: 'just now',
      };
      setCoreMemories(prev => [entry, ...prev]);
      setStoreContent('');
      setStoreMetadata('');
      showMessage('Core memory stored (offline mode)', 'info');
    }
  };

  const handleStoreSession = async () => {
    if (!storeContent.trim()) { showMessage('Content is required', 'error'); return; }
    try {
      const metadata = storeMetadata ? JSON.parse(storeMetadata) : {};
      const res = await fetch(`${apiBase}/layered-memory/store-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: storeContent,
          category: storeCategory,
          priority: storePriority,
          metadata,
          source: storeSource,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const entry: MemoryEntry = {
        id: data.id || uid(),
        content: data.content || storeContent,
        category: data.category || storeCategory,
        priority: data.priority || storePriority,
        metadata: data.metadata || metadata,
        source: data.source || storeSource,
        layer: 'session',
        created_at: 'just now',
      };
      setSessionMemories(prev => [entry, ...prev]);
      setStoreContent('');
      setStoreMetadata('');
      showMessage('Session memory stored', 'success');
      fetchStats();
    } catch {
      const entry: MemoryEntry = {
        id: uid(),
        content: storeContent,
        category: storeCategory,
        priority: storePriority,
        metadata: storeMetadata ? JSON.parse(storeMetadata) : {},
        source: storeSource,
        layer: 'session',
        created_at: 'just now',
      };
      setSessionMemories(prev => [entry, ...prev]);
      setStoreContent('');
      setStoreMetadata('');
      showMessage('Session memory stored (offline mode)', 'info');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) { showMessage('Search query is required', 'error'); return; }
    try {
      const params = new URLSearchParams({ query: searchQuery, limit: searchLimit });
      if (searchLayers.trim()) params.set('layers', searchLayers);
      const res = await fetch(`${apiBase}/layered-memory/search?${params.toString()}`);
      const data = await res.json();
      setSearchResults(data.results || data);
      showMessage(`Found ${(data.results || data).length} results`, 'success');
    } catch {
      setSearchResults(defaultSearchResults);
      showMessage('Search completed (offline mode)', 'info');
    }
  };

  const handleConsolidate = async () => {
    try {
      const res = await fetch(`${apiBase}/layered-memory/consolidate`, { method: 'POST' });
      const data = await res.json();
      setConsolidateResult(data);
      showMessage('Memory consolidation completed', 'success');
      fetchStats();
    } catch {
      setConsolidateResult({
        consolidated_from: 34,
        consolidated_to: 15,
        removed: 19,
        timestamp: new Date().toISOString(),
      });
      showMessage('Consolidation completed (offline mode)', 'info');
    }
  };

  const handleRefresh = async () => {
    await Promise.all([fetchStats(), fetchContext()]);
    showMessage('Layered memory refreshed', 'info');
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83D\uDCCA' },
    { key: 'store-core', label: 'Store Core', icon: '\uD83D\uDCE5' },
    { key: 'store-session', label: 'Store Session', icon: '\uD83D\uDCE4' },
    { key: 'search', label: 'Search', icon: '\uD83D\uDD0D' },
    { key: 'consolidate', label: 'Consolidate', icon: '\uD83D\uDCCE' },
    { key: 'context', label: 'Context', icon: '\uD83D\uDCCB' },
  ];

  const renderStoreForm = (layer: 'core' | 'session') => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{
        padding: 12, backgroundColor: '#22223a', borderRadius: 6,
        border: `1px solid ${layer === 'core' ? '#3d3a6a' : '#2a3a3a'}`,
      }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
          {layer === 'core' ? 'Store Core Memory' : 'Store Session Memory'}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <textarea
            placeholder="Memory content..."
            value={storeContent}
            onChange={e => setStoreContent(e.target.value)}
            style={{
              padding: '8px 10px', fontSize: 12,
              backgroundColor: '#111', color: '#e0e0e0',
              border: '1px solid #333', borderRadius: 4,
              resize: 'vertical', minHeight: 60, outline: 'none',
              fontFamily: 'system-ui, sans-serif',
            }}
          />
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select
              value={storeCategory}
              onChange={e => setStoreCategory(e.target.value)}
              style={{
                padding: '6px 8px', fontSize: 11,
                backgroundColor: '#111', color: '#e0e0e0',
                border: '1px solid #333', borderRadius: 4, outline: 'none',
              }}
            >
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <select
              value={storePriority}
              onChange={e => setStorePriority(e.target.value)}
              style={{
                padding: '6px 8px', fontSize: 11,
                backgroundColor: '#111', color: '#e0e0e0',
                border: '1px solid #333', borderRadius: 4, outline: 'none',
              }}
            >
              {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <select
              value={storeSource}
              onChange={e => setStoreSource(e.target.value)}
              style={{
                padding: '6px 8px', fontSize: 11,
                backgroundColor: '#111', color: '#e0e0e0',
                border: '1px solid #333', borderRadius: 4, outline: 'none',
              }}
            >
              {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <input
            type="text"
            placeholder='Metadata (JSON, e.g. {"key": "value"})'
            value={storeMetadata}
            onChange={e => setStoreMetadata(e.target.value)}
            style={{
              padding: '6px 8px', fontSize: 11,
              backgroundColor: '#111', color: '#e0e0e0',
              border: '1px solid #333', borderRadius: 4, outline: 'none',
            }}
          />
          <button
            onClick={layer === 'core' ? handleStoreCore : handleStoreSession}
            style={{
              padding: '8px 16px', fontSize: 12, fontWeight: 600,
              backgroundColor: layer === 'core' ? '#2d3a5a' : '#2d3a4a',
              color: layer === 'core' ? '#a29bfe' : '#00b894',
              border: `1px solid ${layer === 'core' ? '#3d4a6a' : '#3d4a5a'}`,
              borderRadius: 4, cursor: 'pointer',
              alignSelf: 'flex-start',
            }}
          >
            Store in {layer === 'core' ? 'Core' : 'Session'} Layer
          </button>
        </div>
      </div>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#888', marginTop: 4 }}>
        {layer === 'core' ? 'Core' : 'Session'} Memories ({layer === 'core' ? coreMemories.length : sessionMemories.length})
      </div>
      {(layer === 'core' ? coreMemories : sessionMemories).map(mem => (
        <div key={mem.id} style={{
          padding: 10, backgroundColor: '#22223a', borderRadius: 6,
          border: '1px solid #2a2a3e',
          borderLeft: `3px solid ${LAYER_COLORS[mem.layer]}`,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <span style={{
                fontSize: 9, padding: '1px 6px', borderRadius: 3,
                backgroundColor: CATEGORY_COLORS[mem.category] + '33',
                color: CATEGORY_COLORS[mem.category], fontWeight: 600,
                textTransform: 'uppercase',
              }}>{mem.category}</span>
              <span style={{
                fontSize: 9, padding: '1px 6px', borderRadius: 3,
                backgroundColor: PRIORITY_COLORS[mem.priority] + '33',
                color: PRIORITY_COLORS[mem.priority], fontWeight: 600,
                textTransform: 'uppercase',
              }}>{mem.priority}</span>
            </div>
            <span style={{ fontSize: 10, color: '#555' }}>{mem.created_at}</span>
          </div>
          <div style={{ fontSize: 12, color: '#ccc', marginBottom: 4 }}>{mem.content}</div>
          <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#666' }}>
            <span>Source: {mem.source}</span>
            {Object.keys(mem.metadata).length > 0 && (
              <span>Meta: {JSON.stringify(mem.metadata)}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );

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
          <span style={{ fontSize: 16 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Layered Memory</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_memories} total · {stats.total_core_memories} core · {stats.total_session_memories} session
            </span>
          )}
          <button onClick={handleRefresh} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            <i className="fa-solid fa-rotate" />
          </button>
        </div>
      </div>

      {/* Message Banner */}
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

      {/* Tab Bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {stats && (
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', marginBottom: 4,
                display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10,
              }}>
                <div style={{
                  textAlign: 'center', padding: '8px 10px',
                  backgroundColor: '#111', borderRadius: 4,
                }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#6c5ce7' }}>{stats.total_core_memories}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Core Memories</div>
                </div>
                <div style={{
                  textAlign: 'center', padding: '8px 10px',
                  backgroundColor: '#111', borderRadius: 4,
                }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#00b894' }}>{stats.total_session_memories}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Session Memories</div>
                </div>
                <div style={{
                  textAlign: 'center', padding: '8px 10px',
                  backgroundColor: '#111', borderRadius: 4,
                }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#a29bfe' }}>{stats.total_memories}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Total Memories</div>
                </div>
                <div style={{
                  textAlign: 'center', padding: '8px 10px',
                  backgroundColor: '#111', borderRadius: 4,
                }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#fdcb6e' }}>{stats.consolidation_count}</div>
                  <div style={{ fontSize: 10, color: '#888' }}>Consolidations</div>
                </div>
              </div>
            )}
            {stats?.last_consolidation && (
              <div style={{
                padding: '8px 12px', backgroundColor: '#22223a', borderRadius: 4,
                border: '1px solid #2a2a3e', fontSize: 11, color: '#888',
                display: 'flex', justifyContent: 'space-between',
              }}>
                <span>Last consolidation</span>
                <span style={{ color: '#aaa' }}>{stats.last_consolidation}</span>
              </div>
            )}

            {/* Core memories preview */}
            <div style={{ fontSize: 11, fontWeight: 600, color: '#a29bfe', marginTop: 4 }}>
              {'\uD83D\uDCE5'} Core Memories ({coreMemories.length})
            </div>
            {coreMemories.slice(0, 3).map(mem => (
              <div key={mem.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: '3px solid #6c5ce7',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: CATEGORY_COLORS[mem.category] + '33',
                    color: CATEGORY_COLORS[mem.category], fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{mem.category}</span>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: PRIORITY_COLORS[mem.priority] + '33',
                    color: PRIORITY_COLORS[mem.priority], fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{mem.priority}</span>
                  <span style={{ fontSize: 10, color: '#555', marginLeft: 'auto' }}>{mem.created_at}</span>
                </div>
                <div style={{ fontSize: 12, color: '#ccc' }}>{mem.content}</div>
              </div>
            ))}

            {/* Session memories preview */}
            <div style={{ fontSize: 11, fontWeight: 600, color: '#00b894', marginTop: 4 }}>
              {'\uD83D\uDCE4'} Session Memories ({sessionMemories.length})
            </div>
            {sessionMemories.slice(0, 3).map(mem => (
              <div key={mem.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: '3px solid #00b894',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: CATEGORY_COLORS[mem.category] + '33',
                    color: CATEGORY_COLORS[mem.category], fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{mem.category}</span>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: PRIORITY_COLORS[mem.priority] + '33',
                    color: PRIORITY_COLORS[mem.priority], fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{mem.priority}</span>
                  <span style={{ fontSize: 10, color: '#555', marginLeft: 'auto' }}>{mem.created_at}</span>
                </div>
                <div style={{ fontSize: 12, color: '#ccc' }}>{mem.content}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'store-core' && renderStoreForm('core')}

        {activeTab === 'store-session' && renderStoreForm('session')}

        {activeTab === 'search' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD0D'} Search Memories
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    type="text"
                    placeholder="Search query..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    style={{
                      flex: 1, padding: '8px 10px', fontSize: 12,
                      backgroundColor: '#111', color: '#e0e0e0',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}
                  />
                  <button onClick={handleSearch} style={{
                    padding: '8px 16px', fontSize: 12, fontWeight: 600,
                    backgroundColor: '#6c5ce7', color: '#fff',
                    border: 'none', borderRadius: 4, cursor: 'pointer',
                  }}>
                    {'\uD83D\uDD0D'} Search
                  </button>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input
                    type="text"
                    placeholder="Layers (e.g. core,session)"
                    value={searchLayers}
                    onChange={e => setSearchLayers(e.target.value)}
                    style={{
                      width: 180, padding: '6px 8px', fontSize: 11,
                      backgroundColor: '#111', color: '#e0e0e0',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}
                  />
                  <input
                    type="number"
                    placeholder="Limit"
                    value={searchLimit}
                    onChange={e => setSearchLimit(e.target.value)}
                    min="1"
                    max="100"
                    style={{
                      width: 80, padding: '6px 8px', fontSize: 11,
                      backgroundColor: '#111', color: '#e0e0e0',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}
                  />
                  <span style={{ fontSize: 10, color: '#666' }}>limit</span>
                </div>
              </div>
            </div>

            {searchResults.length > 0 ? (
              searchResults.map((result, idx) => (
                <div key={result.entry?.id || idx} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${LAYER_COLORS[result.layer] || '#6c5ce7'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: (LAYER_COLORS[result.layer] || '#6c5ce7') + '33',
                        color: LAYER_COLORS[result.layer] || '#6c5ce7', fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{result.layer}</span>
                      {result.entry && (
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: CATEGORY_COLORS[result.entry.category] + '33',
                          color: CATEGORY_COLORS[result.entry.category], fontWeight: 600,
                          textTransform: 'uppercase',
                        }}>{result.entry.category}</span>
                      )}
                    </div>
                    <span style={{
                      fontSize: 10, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600,
                    }}>
                      {(result.relevance * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <div style={{
                    padding: '6px 8px', backgroundColor: '#111', borderRadius: 3,
                    fontSize: 11, color: '#aaa', marginBottom: 4,
                  }}>
                    {result.snippet}
                  </div>
                  {result.entry && (
                    <div style={{ display: 'flex', gap: 8, fontSize: 10, color: '#666' }}>
                      <span>Priority: {result.entry.priority}</span>
                      <span>Source: {result.entry.source}</span>
                      <span>{result.entry.created_at}</span>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD0D'}</span>
                Enter a query above to search across memory layers
              </div>
            )}
          </div>
        )}

        {activeTab === 'consolidate' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCE'} Memory Consolidation
              </div>
              <div style={{ fontSize: 11, color: '#888', marginBottom: 10 }}>
                Consolidation moves high-value session memories into core memory, deduplicates,
                and removes stale entries. This helps keep the memory layers efficient and relevant.
              </div>
              <button onClick={handleConsolidate} style={{
                padding: '8px 16px', fontSize: 12, fontWeight: 600,
                backgroundColor: '#2d4a3a', color: '#6bcb77',
                border: '1px solid #3d5a4a', borderRadius: 4, cursor: 'pointer',
              }}>
                {'\uD83D\uDCCE'} Run Consolidation
              </button>
            </div>

            {consolidateResult && (
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#6bcb77', marginBottom: 8 }}>
                  {'\u2705'} Last Consolidation Result
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
                  <div style={{
                    textAlign: 'center', padding: '8px 10px',
                    backgroundColor: '#111', borderRadius: 4,
                  }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>{consolidateResult.consolidated_from}</div>
                    <div style={{ fontSize: 10, color: '#888' }}>From (session)</div>
                  </div>
                  <div style={{
                    textAlign: 'center', padding: '8px 10px',
                    backgroundColor: '#111', borderRadius: 4,
                  }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#6c5ce7' }}>{consolidateResult.consolidated_to}</div>
                    <div style={{ fontSize: 10, color: '#888' }}>To (core)</div>
                  </div>
                  <div style={{
                    textAlign: 'center', padding: '8px 10px',
                    backgroundColor: '#111', borderRadius: 4,
                  }}>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#ff6b6b' }}>{consolidateResult.removed}</div>
                    <div style={{ fontSize: 10, color: '#888' }}>Removed</div>
                  </div>
                  <div style={{
                    textAlign: 'center', padding: '8px 10px',
                    backgroundColor: '#111', borderRadius: 4,
                  }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa' }}>
                      {new Date(consolidateResult.timestamp).toLocaleTimeString()}
                    </div>
                    <div style={{ fontSize: 10, color: '#888' }}>Timestamp</div>
                  </div>
                </div>
              </div>
            )}

            {!consolidateResult && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCE'}</span>
                Click &quot;Run Consolidation&quot; to consolidate session memories into core memory
              </div>
            )}
          </div>
        )}

        {activeTab === 'context' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCB'} Memory Context
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: '#888' }}>Max Tokens:</span>
                <input
                  type="number"
                  value={contextMaxTokens}
                  onChange={e => setContextMaxTokens(e.target.value)}
                  min="100"
                  max="10000"
                  style={{
                    width: 100, padding: '6px 8px', fontSize: 11,
                    backgroundColor: '#111', color: '#e0e0e0',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}
                />
                <button onClick={fetchContext} style={{
                  padding: '6px 12px', fontSize: 11, fontWeight: 600,
                  backgroundColor: '#6c5ce7', color: '#fff',
                  border: 'none', borderRadius: 4, cursor: 'pointer',
                }}>
                  {'\uD83D\uDD04'} Refresh
                </button>
              </div>
            </div>

            {contextResult && (
              <>
                <div style={{
                  padding: '8px 12px', backgroundColor: '#22223a', borderRadius: 4,
                  border: '1px solid #2a2a3e', fontSize: 11, color: '#888',
                  display: 'flex', justifyContent: 'space-between',
                }}>
                  <span>Tokens Used</span>
                  <span style={{ color: '#a29bfe', fontWeight: 600 }}>
                    {contextResult.tokens_used} / {contextResult.max_tokens}
                  </span>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                    Context Text ({contextResult.entries.length} entries)
                  </div>
                  <div style={{
                    padding: '8px 10px', backgroundColor: '#111', borderRadius: 4,
                    fontFamily: 'monospace', fontSize: 11, color: '#ccc',
                    maxHeight: 150, overflow: 'auto', whiteSpace: 'pre-wrap',
                    lineHeight: 1.5,
                  }}>
                    {contextResult.context_text}
                  </div>
                </div>

                {contextResult.entries.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#888' }}>
                      Context Entries
                    </div>
                    {contextResult.entries.map(entry => (
                      <div key={entry.id} style={{
                        padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                        border: '1px solid #2a2a3e',
                        borderLeft: `3px solid ${LAYER_COLORS[entry.layer] || '#6c5ce7'}`,
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3, flexWrap: 'wrap' }}>
                          <span style={{
                            fontSize: 9, padding: '1px 6px', borderRadius: 3,
                            backgroundColor: (LAYER_COLORS[entry.layer] || '#6c5ce7') + '33',
                            color: LAYER_COLORS[entry.layer] || '#6c5ce7', fontWeight: 600,
                            textTransform: 'uppercase',
                          }}>{entry.layer}</span>
                          <span style={{
                            fontSize: 9, padding: '1px 6px', borderRadius: 3,
                            backgroundColor: CATEGORY_COLORS[entry.category] + '33',
                            color: CATEGORY_COLORS[entry.category], fontWeight: 600,
                            textTransform: 'uppercase',
                          }}>{entry.category}</span>
                          <span style={{ fontSize: 10, color: '#555', marginLeft: 'auto' }}>{entry.created_at}</span>
                        </div>
                        <div style={{ fontSize: 12, color: '#ccc' }}>{entry.content}</div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {!contextResult && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCCB'}</span>
                Loading context...
              </div>
            )}
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
        <span>
          {'\uD83E\uDDE0'} {coreMemories.length} core · {sessionMemories.length} session
        </span>
        <span>
          {stats ? `${stats.total_memories} total · ${stats.consolidation_count} consolidations` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default AgentLayeredMemoryPanel;