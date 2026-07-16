import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'scrub' | 'rules';

interface ScrubRule {
  id: string;
  block_type: string;
  visibility: string;
}

interface SessionStats {
  chunks_processed: number;
  blocks_removed: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const StreamingScrubberPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('scrub');
  const [loading, setLoading] = useState(false);

  const [rules, setRules] = useState<ScrubRule[]>([]);
  const [stats, setStats] = useState<SessionStats | null>(null);
  const [scrubbedOutput, setScrubbedOutput] = useState('');

  const [inputText, setInputText] = useState('');
  const [sessionName, setSessionName] = useState('');
  const [blockType, setBlockType] = useState('tool_call');
  const [visibility, setVisibility] = useState('hidden');

  const apiBase = API_ROOT + '/agent';

  const defaultRules: ScrubRule[] = [
    { id: uid(), block_type: 'xml_fence', visibility: 'hidden' },
    { id: uid(), block_type: 'tool_result', visibility: 'truncated' },
    { id: uid(), block_type: 'thinking', visibility: 'removed' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/streaming-scrubber/stats`);
      const data = await res.json();
      if (data.rules) setRules(data.rules);
      if (data.stats) setStats(data.stats);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setRules(defaultRules);
    setStats({ chunks_processed: 1423, blocks_removed: 87 });
    fetchStats();
  }, [fetchStats]);

  const handleCreateSession = async () => {
    if (!sessionName.trim()) { showMessage('Session name is required', 'error'); return; }
    if (!inputText.trim()) { showMessage('Input text is required', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/streaming-scrubber/create-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: sessionName, input: inputText }),
      });
      const data = await res.json();
      if (data.output) setScrubbedOutput(data.output);
      showMessage(`Session "${sessionName}" created`, 'success');
      setSessionName('');
      setInputText('');
    } catch {
      const scrubbed = inputText
        .replace(/<function_calls>[\s\S]*?<\/function_calls>/g, '[tool calls removed]')
        .replace(/<thinking>[\s\S]*?<\/thinking>/g, '[thinking hidden]');
      setScrubbedOutput(scrubbed);
      showMessage(`Scrubbed locally (offline fallback)`, 'info');
      setSessionName('');
      setInputText('');
    }
    setLoading(false);
  };

  const handleAddRule = async () => {
    if (!blockType.trim()) { showMessage('Block type is required', 'error'); return; }
    setLoading(true);
    try {
      await fetch(`${apiBase}/streaming-scrubber/add-rule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ block_type: blockType, visibility }),
      });
      const newRule: ScrubRule = { id: uid(), block_type: blockType, visibility };
      setRules(prev => [...prev, newRule]);
      showMessage(`Rule added: ${blockType}`, 'success');
      setBlockType('');
    } catch {
      const newRule: ScrubRule = { id: uid(), block_type: blockType, visibility };
      setRules(prev => [...prev, newRule]);
      showMessage(`Rule added (offline fallback)`, 'info');
      setBlockType('');
    }
    setLoading(false);
  };

  const tabItems: { key: TabId; label: string }[] = [
    { key: 'scrub', label: 'Scrub' },
    { key: 'rules', label: 'Rules' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDF9'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Streaming Scrubber</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{stats ? `${stats.chunks_processed} chunks · ${stats.blocks_removed} removed` : ''}</span>
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
        {activeTab === 'scrub' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Create Scrubbing Session</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <input value={sessionName} onChange={e => setSessionName(e.target.value)} placeholder="Session name" style={{ ...inputStyle, width: '100%' }} />
                <textarea value={inputText} onChange={e => setInputText(e.target.value)} placeholder="Paste text with XML fences, tool calls, etc." style={{ ...inputStyle, width: '100%', minHeight: 100, resize: 'vertical' }} />
                <button onClick={handleCreateSession} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Scrub</button>
              </div>
            </div>

            {scrubbedOutput && (
              <div style={{ padding: 12, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#66bb6a', marginBottom: 8 }}>Scrubbed Output</div>
                <pre style={{ margin: 0, fontSize: 11, color: '#aaa', whiteSpace: 'pre-wrap', backgroundColor: '#0d0d0d', padding: 12, borderRadius: 4, overflowX: 'auto' }}>{scrubbedOutput}</pre>
              </div>
            )}

            {stats && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>Session Stats</div>
                <div style={{ display: 'flex', gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 10, color: '#888' }}>Chunks Processed</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#4fc3f7' }}>{stats.chunks_processed}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#888' }}>Blocks Removed</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#ef5350' }}>{stats.blocks_removed}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'rules' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>Add Scrub Rule</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <select value={blockType} onChange={e => setBlockType(e.target.value)} style={{ ...inputStyle, width: 160 }}>
                  <option value="tool_call">tool_call</option>
                  <option value="tool_result">tool_result</option>
                  <option value="xml_fence">xml_fence</option>
                  <option value="thinking">thinking</option>
                  <option value="code_block">code_block</option>
                </select>
                <select value={visibility} onChange={e => setVisibility(e.target.value)} style={{ ...inputStyle, width: 140 }}>
                  <option value="hidden">hidden</option>
                  <option value="truncated">truncated</option>
                  <option value="removed">removed</option>
                  <option value="visible">visible</option>
                </select>
                <button onClick={handleAddRule} disabled={loading} style={{ padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77', border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Add Rule</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Rules ({rules.length})</div>
            {rules.map(rule => (
              <div key={rule.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontSize: 12, color: '#ccc', fontFamily: 'monospace' }}>{rule.block_type}</span>
                  <span style={{ fontSize: 10, color: '#666', marginLeft: 8 }}>XML fence blocks</span>
                </div>
                <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 3, backgroundColor: rule.visibility === 'hidden' ? '#3a2a1a' : rule.visibility === 'removed' ? '#3a1a1a' : '#1a3a1a', color: rule.visibility === 'hidden' ? '#ffa726' : rule.visibility === 'removed' ? '#ef5350' : '#66bb6a' }}>{rule.visibility}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83E\uDDF9'} {rules.length} rules</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default StreamingScrubberPanel;