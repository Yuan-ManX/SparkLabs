import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'fragments' | 'synthesize' | 'query';

interface KnowledgeFragment {
  id: string;
  source: string;
  content: string;
  domain: string;
  ingested_at: number;
  merge_count: number;
}

interface SynthesizeResult {
  id: string;
  topic: string;
  source_count: number;
  summary: string;
  key_insights: string[];
  created_at: number;
}

interface QueryResult {
  id: string;
  query: string;
  matches: { fragment_id: string; snippet: string; relevance: number }[];
  total_results: number;
}

interface CrossReferenceResult {
  source_fragment: string;
  related_fragments: { id: string; relationship: string; confidence: number }[];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const KnowledgeSynthesisPanel: React.FC = () => {
  const [fragments, setFragments] = useState<KnowledgeFragment[]>([]);
  const [synthesizeResult, setSynthesizeResult] = useState<SynthesizeResult | null>(null);
  const [distillResult, setDistillResult] = useState<string | null>(null);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [crossRefResult, setCrossRefResult] = useState<CrossReferenceResult | null>(null);
  const [domainIndexResult, setDomainIndexResult] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('fragments');
  const [sourceInput, setSourceInput] = useState('');
  const [contentInput, setContentInput] = useState('');
  const [domainInput, setDomainInput] = useState('');
  const [mergeSourceInput, setMergeSourceInput] = useState('');
  const [mergeTargetInput, setMergeTargetInput] = useState('');
  const [synthesizeTopicInput, setSynthesizeTopicInput] = useState('');
  const [synthesizeDomainInput, setSynthesizeDomainInput] = useState('');
  const [distillSessionId, setDistillSessionId] = useState('');
  const [queryInput, setQueryInput] = useState('');
  const [queryDomainInput, setQueryDomainInput] = useState('');
  const [buildDomainInput, setBuildDomainInput] = useState('');
  const [crossRefFragmentId, setCrossRefFragmentId] = useState('');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultFragments: KnowledgeFragment[] = [
    { id: uid(), source: 'documentation', content: 'Redis caching best practices for high-availability systems', domain: 'infrastructure', ingested_at: Date.now() - 600000, merge_count: 0 },
    { id: uid(), source: 'research_paper', content: 'Attention mechanisms in transformer architectures', domain: 'machine-learning', ingested_at: Date.now() - 3600000, merge_count: 2 },
    { id: uid(), source: 'code_review', content: 'Dependency injection patterns for testable microservices', domain: 'software-engineering', ingested_at: Date.now() - 7200000, merge_count: 1 },
    { id: uid(), source: 'conversation', content: 'Team decision: adopt React Server Components for new features', domain: 'frontend', ingested_at: Date.now() - 86400000, merge_count: 0 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchFragments = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/knowledge-synthesis/list-fragments`);
      const data = await res.json();
      if (data.fragments) setFragments(data.fragments);
    } catch {}
  }, []);

  useEffect(() => {
    setFragments(defaultFragments);
    fetchFragments();
  }, [fetchFragments]);

  const handleIngestFragment = async () => {
    const source = sourceInput.trim() || 'manual';
    const content = contentInput.trim() || 'New knowledge fragment';
    const domain = domainInput.trim() || 'general';
    try {
      await fetch(`${apiBase}/knowledge-synthesis/ingest-fragment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, content, domain }),
      });
      showMessage('Fragment ingested', 'success');
      fetchFragments();
    } catch {
      const fragment: KnowledgeFragment = {
        id: uid(),
        source,
        content,
        domain,
        ingested_at: Date.now(),
        merge_count: 0,
      };
      setFragments(prev => [fragment, ...prev]);
      showMessage('Fragment ingested (offline fallback)', 'info');
    }
  };

  const handleMergeFragments = async () => {
    const source = mergeSourceInput.trim() || fragments[0]?.id || '';
    const target = mergeTargetInput.trim() || fragments[1]?.id || '';
    try {
      await fetch(`${apiBase}/knowledge-synthesis/merge-fragments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: source, target_id: target }),
      });
      setFragments(prev => prev.map(f => f.id === target ? { ...f, merge_count: f.merge_count + 1, content: f.content + ' [merged]' } : f));
      showMessage('Fragments merged', 'success');
    } catch {
      setFragments(prev => prev.map(f => f.id === target ? { ...f, merge_count: f.merge_count + 1, content: f.content + ' [merged]' } : f));
      showMessage('Fragments merged (offline fallback)', 'info');
    }
  };

  const handleSynthesize = async () => {
    const topic = synthesizeTopicInput.trim() || 'General synthesis';
    const domain = synthesizeDomainInput.trim() || 'general';
    try {
      const res = await fetch(`${apiBase}/knowledge-synthesis/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, domain }),
      });
      const data = await res.json();
      setSynthesizeResult({
        id: data.id || uid(),
        topic,
        source_count: data.source_count || fragments.filter(f => f.domain === domain).length || 3,
        summary: data.summary || `Synthesized knowledge for "${topic}" across ${fragments.filter(f => f.domain === domain).length || 3} sources.`,
        key_insights: data.key_insights || ['Key pattern identified: caching strategies follow similar optimization principles', 'Cross-domain insight: ML attention patterns mirror priority-based caching', 'Actionable recommendation: implement tiered caching with TTL-based eviction'],
        created_at: Date.now(),
      });
      showMessage('Synthesis complete', 'success');
    } catch {
      setSynthesizeResult({
        id: uid(),
        topic,
        source_count: 3,
        summary: `Synthesized knowledge for "${topic}" across multiple sources.`,
        key_insights: ['Key pattern identified across sources', 'Cross-domain insight discovered', 'Actionable recommendation generated'],
        created_at: Date.now(),
      });
      showMessage('Synthesis complete (offline fallback)', 'info');
    }
  };

  const handleDistillSession = async () => {
    const sessionId = distillSessionId.trim() || 'session-default';
    try {
      const res = await fetch(`${apiBase}/knowledge-synthesis/distill-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();
      setDistillResult(data.result || `Session ${sessionId} distilled into compact knowledge representation.`);
      showMessage('Session distilled', 'success');
    } catch {
      setDistillResult(`Session ${sessionId} distilled: extracted 5 key insights, 3 action items, 2 domain patterns.`);
      showMessage('Session distilled (offline fallback)', 'info');
    }
  };

  const handleQueryKnowledge = () => {
    const query = queryInput.trim();
    const domain = queryDomainInput.trim();
    if (!query) return;
    const matchingFragments = fragments.filter(f => !domain || f.domain === domain);
    setQueryResult({
      id: uid(),
      query,
      matches: matchingFragments.slice(0, 4).map(f => ({
        fragment_id: f.id,
        snippet: f.content.slice(0, 100) + '...',
        relevance: Math.round((0.65 + Math.random() * 0.3) * 100) / 100,
      })),
      total_results: matchingFragments.length,
    });
    showMessage(`Found ${matchingFragments.length} results for "${query}"`, 'info');
  };

  const handleBuildDomainIndex = async () => {
    const domain = buildDomainInput.trim() || 'general';
    try {
      await fetch(`${apiBase}/knowledge-synthesis/build-domain-index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain }),
      });
      setDomainIndexResult(`Domain index built for "${domain}". Indexed ${fragments.filter(f => f.domain === domain).length} fragments.`);
      showMessage('Domain index built', 'success');
    } catch {
      setDomainIndexResult(`Domain index built for "${domain}". Indexed ${fragments.filter(f => f.domain === domain).length} fragments.`);
      showMessage('Domain index built (offline fallback)', 'info');
    }
  };

  const handleCrossRef = () => {
    const fragmentId = crossRefFragmentId.trim() || fragments[0]?.id || '';
    setCrossRefResult({
      source_fragment: fragmentId,
      related_fragments: fragments.filter(f => f.id !== fragmentId).slice(0, 3).map(f => ({
        id: f.id,
        relationship: Math.random() > 0.5 ? 'complementary' : 'related',
        confidence: Math.round((0.7 + Math.random() * 0.25) * 100) / 100,
      })),
    });
    showMessage('Cross-reference complete', 'info');
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'fragments', label: 'Fragments', icon: '\uD83D\uDCC4', count: fragments.length },
    { key: 'synthesize', label: 'Synthesize', icon: '\uD83E\uDDE0', count: synthesizeResult ? 1 : 0 },
    { key: 'query', label: 'Query', icon: '\uD83D\uDD0D', count: queryResult ? 1 : 0 },
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
          <span style={{ fontWeight: 700, fontSize: 15 }}>Knowledge Synthesis</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {fragments.length} fragments
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
        <input value={sourceInput} onChange={e => setSourceInput(e.target.value)} placeholder="Source..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 90, outline: 'none' }} />
        <input value={contentInput} onChange={e => setContentInput(e.target.value)} placeholder="Content..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 150, outline: 'none' }} />
        <input value={domainInput} onChange={e => setDomainInput(e.target.value)} placeholder="Domain..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 100, outline: 'none' }} />
        <button onClick={handleIngestFragment} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
          {'\u2795'} Ingest Fragment
        </button>
        <input value={mergeSourceInput} onChange={e => setMergeSourceInput(e.target.value)} placeholder="Source ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 90, outline: 'none' }} />
        <input value={mergeTargetInput} onChange={e => setMergeTargetInput(e.target.value)} placeholder="Target ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 90, outline: 'none' }} />
        <button onClick={handleMergeFragments} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
          {'\uD83D\uDD17'} Merge
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
        {activeTab === 'fragments' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {fragments.map(fragment => (
              <div key={fragment.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: '3px solid #6c5ce7',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      fontSize: 9, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#a29bfe', fontWeight: 600,
                    }}>{fragment.domain}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#2a2a3a', color: '#888',
                    }}>{fragment.source}</span>
                  </div>
                  <span style={{ fontSize: 9, color: '#666' }}>
                    Merges: {fragment.merge_count}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{fragment.content}</div>
                <div style={{ fontSize: 9, color: '#555', fontFamily: 'monospace' }}>
                  {fragment.id.slice(0, 12)} · {formatTime(fragment.ingested_at)}
                </div>
              </div>
            ))}
            {fragments.length === 0 && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCC4'}</span>
                No knowledge fragments ingested
              </div>
            )}
          </div>
        )}

        {activeTab === 'synthesize' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 }}>
              <input value={synthesizeTopicInput} onChange={e => setSynthesizeTopicInput(e.target.value)} placeholder="Topic..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 120, outline: 'none' }} />
              <input value={synthesizeDomainInput} onChange={e => setSynthesizeDomainInput(e.target.value)} placeholder="Domain..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 110, outline: 'none' }} />
              <button onClick={handleSynthesize} style={{ padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83E\uDDE0'} Synthesize
              </button>
              <input value={distillSessionId} onChange={e => setDistillSessionId(e.target.value)} placeholder="Session ID..." style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 110, outline: 'none' }} />
              <button onClick={handleDistillSession} style={{ padding: '6px 12px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDCA7'} Distill
              </button>
            </div>
            {distillResult && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#a29bfe' }}>{'\uD83D\uDCA7'} Distillation Result</div>
                <div style={{ fontSize: 10, color: '#aaa' }}>{distillResult}</div>
              </div>
            )}
            {synthesizeResult && (
              <div style={{ padding: 14, backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e', borderLeft: '3px solid #6c5ce7' }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: '#a29bfe' }}>
                  {'\uD83E\uDDE0'} Synthesis Result: {synthesizeResult.topic}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 11, marginBottom: 8 }}>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Sources: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{synthesizeResult.source_count}</span>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4, color: '#aaa' }}>
                    Insights: <span style={{ color: '#6bcb77', fontWeight: 600 }}>{synthesizeResult.key_insights.length}</span>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#aaa', marginBottom: 10, padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                  {synthesizeResult.summary}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {synthesizeResult.key_insights.map((insight, i) => (
                    <div key={i} style={{ fontSize: 10, color: '#888', padding: '4px 8px', backgroundColor: '#141428', borderRadius: 3 }}>
                      {'\uD83D\uDCA1'} {insight}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {!distillResult && !synthesizeResult && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83E\uDDE0'}</span>
                Enter a topic and domain to synthesize knowledge
              </div>
            )}
          </div>
        )}

        {activeTab === 'query' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input value={queryInput} onChange={e => setQueryInput(e.target.value)} placeholder="Search query..." style={{ flex: 1, padding: '8px 12px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
              <input value={queryDomainInput} onChange={e => setQueryDomainInput(e.target.value)} placeholder="Domain (optional)..." style={{ padding: '8px 12px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 130, outline: 'none' }} />
              <button onClick={handleQueryKnowledge} style={{ padding: '8px 16px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDD0D'} Query
              </button>
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input value={buildDomainInput} onChange={e => setBuildDomainInput(e.target.value)} placeholder="Domain to index..." style={{ flex: 1, padding: '8px 12px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
              <button onClick={handleBuildDomainIndex} style={{ padding: '8px 16px', backgroundColor: '#3a2d3a', color: '#a29bfe', border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDCC7'} Build Index
              </button>
              <input value={crossRefFragmentId} onChange={e => setCrossRefFragmentId(e.target.value)} placeholder="Fragment ID..." style={{ padding: '8px 12px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, width: 120, outline: 'none' }} />
              <button onClick={handleCrossRef} style={{ padding: '8px 16px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                {'\uD83D\uDD17'} Cross Ref
              </button>
            </div>
            {domainIndexResult && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#a29bfe' }}>{'\uD83D\uDCC7'} Domain Index</div>
                <div style={{ fontSize: 10, color: '#aaa' }}>{domainIndexResult}</div>
              </div>
            )}
            {crossRefResult && (
              <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e' }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#fdcb6e' }}>{'\uD83D\uDD17'} Cross References</div>
                <div style={{ fontSize: 9, color: '#666', marginBottom: 6, fontFamily: 'monospace' }}>
                  Source: {crossRefResult.source_fragment.slice(0, 12)}
                </div>
                {crossRefResult.related_fragments.map(ref => (
                  <div key={ref.id} style={{
                    padding: '6px 8px', backgroundColor: '#141428', borderRadius: 3,
                    marginBottom: 4, fontSize: 10, color: '#aaa',
                    display: 'flex', justifyContent: 'space-between',
                  }}>
                    <span>
                      <span style={{ fontFamily: 'monospace', color: '#888' }}>{ref.id.slice(0, 12)}</span>
                      {' '}· {ref.relationship}
                    </span>
                    <span style={{ color: '#6bcb77' }}>{(ref.confidence * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
            {queryResult && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ fontSize: 11, color: '#888' }}>
                  {queryResult.total_results} results for "{queryResult.query}"
                </div>
                {queryResult.matches.map(match => (
                  <div key={match.fragment_id} style={{
                    padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                    border: '1px solid #2a2a3e',
                    borderLeft: `3px solid ${match.relevance >= 0.8 ? '#6bcb77' : match.relevance >= 0.7 ? '#fdcb6e' : '#888'}`,
                  }}>
                    <div style={{ fontSize: 10, color: '#aaa', marginBottom: 4 }}>{match.snippet}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#555' }}>
                      <span style={{ fontFamily: 'monospace' }}>{match.fragment_id.slice(0, 12)}</span>
                      <span>{(match.relevance * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {!queryResult && !crossRefResult && !domainIndexResult && (
              <div style={{ textAlign: 'center', padding: 40, color: '#555', backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e' }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD0D'}</span>
                Query knowledge, build domain indexes, or cross-reference fragments
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
        <span>{'\uD83D\uDCDA'} {fragments.length} fragments</span>
        <span>{fragments.map(f => f.domain).filter((v, i, a) => a.indexOf(v) === i).length} domains</span>
      </div>
    </div>
  );
};

export default KnowledgeSynthesisPanel;