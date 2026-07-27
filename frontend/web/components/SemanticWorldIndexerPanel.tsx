import React, { useState, useEffect, useCallback } from 'react';
import { semanticIndexerApi } from '../utils/api';

// Type definitions for the semantic world indexer data shapes

interface IndexerStats {
  total_queries: number;
  total_links_built: number;
  total_relations_decayed: number;
  avg_query_time_ms: number;
  category_distribution: Record<string, number>;
  relation_distribution: Record<string, number>;
}

interface IndexerStatus {
  active: boolean;
  cycle_count: number;
  total_entities: number;
  total_relations: number;
  pending_ingest: number;
  stats: IndexerStats;
}

interface IndexerEntity {
  entity_id: string;
  name: string;
  category: string;
  position: { x: number; y: number; z: number } | number[];
  tags: string[];
  semantic_roles: string[];
}

interface IndexerRelation {
  relation_id: string;
  source_id: string;
  target_id: string;
  relation: string;
  weight: number;
  metadata: Record<string, unknown>;
}

interface IndexerQuery {
  query_id: string;
  query_text: string;
  result_count: number;
  timestamp: string;
}

type TabId = 'entities' | 'query' | 'stats';

// Helper to normalize an API response and pull out the data payload
const unwrap = <T,>(res: unknown): T => {
  const r = res as { status?: string; data?: unknown };
  return (r && r.data !== undefined ? r.data : res) as T;
};

// Format a position value that may be an array or an xyz object
const formatPosition = (pos: IndexerEntity['position']): string => {
  if (Array.isArray(pos)) return `(${pos.join(', ')})`;
  if (pos && typeof pos === 'object') {
    return `(${pos.x}, ${pos.y}, ${pos.z})`;
  }
  return String(pos ?? 'N/A');
};

const SemanticWorldIndexerPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('entities');
  const [status, setStatus] = useState<IndexerStatus | null>(null);
  const [entities, setEntities] = useState<IndexerEntity[]>([]);
  const [relations, setRelations] = useState<IndexerRelation[]>([]);
  const [queries, setQueries] = useState<IndexerQuery[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  // Fetch all panel data from the semantic indexer API
  const fetchData = useCallback(async () => {
    try {
      const [statusRes, entitiesRes, relationsRes, queriesRes] = await Promise.all([
        semanticIndexerApi.getStatus(),
        semanticIndexerApi.getEntities(50),
        semanticIndexerApi.getRelations(50),
        semanticIndexerApi.getQueries(50),
      ]);
      setStatus(unwrap<IndexerStatus>(statusRes));
      setEntities(unwrap<IndexerEntity[]>(entitiesRes) || []);
      setRelations(unwrap<IndexerRelation[]>(relationsRes) || []);
      setQueries(unwrap<IndexerQuery[]>(queriesRes) || []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load indexer data');
    }
  }, []);

  // Initial load and auto-refresh every 3 seconds while the indexer is active
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Trigger a single indexer cycle
  const handleRunCycle = async () => {
    setLoading(true);
    try {
      await semanticIndexerApi.runCycle();
      showMessage('Cycle executed', 'success');
      await fetchData();
    } catch (e) {
      showMessage(e instanceof Error ? e.message : 'Run cycle failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Run a batch of simulated cycles to populate the index
  const handleSimulate = async () => {
    setLoading(true);
    try {
      const res = await semanticIndexerApi.simulate(10);
      const data = unwrap<{ cycles_run?: number }>(res);
      showMessage(`Simulated ${data.cycles_run ?? 10} cycles`, 'success');
      await fetchData();
    } catch (e) {
      showMessage(e instanceof Error ? e.message : 'Simulate failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Reset the entire semantic index
  const handleReset = async () => {
    setLoading(true);
    try {
      await semanticIndexerApi.reset();
      showMessage('Index reset', 'success');
      await fetchData();
    } catch (e) {
      showMessage(e instanceof Error ? e.message : 'Reset failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const stats = status?.stats;
  const categoryDist = stats?.category_distribution || {};
  const relationDist = stats?.relation_distribution || {};
  const maxRelationCount = Math.max(1, ...Object.values(relationDist));

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'entities', label: 'Entities & Relations', icon: 'fa-diagram-project' },
    { id: 'query', label: 'Query & Path', icon: 'fa-route' },
    { id: 'stats', label: 'History & Stats', icon: 'fa-chart-simple' },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0d0d0d] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <i className="fa-solid fa-diagram-project text-[16px] text-[#e0e0e0]" />
          <span className="font-bold text-[15px]">Semantic World Indexer</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-[#555]">
          <span
            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${
              status?.active ? 'bg-[#1a1a1a] text-[#999]' : 'bg-[#161616] text-[#555]'
            }`}
          >
            <i className={`fa-solid fa-circle text-[6px] ${status?.active ? 'text-[#e0e0e0]' : 'text-[#555]'}`} />
            {status?.active ? 'ACTIVE' : 'IDLE'}
          </span>
        </div>
      </div>

      {/* Inline message banner */}
      {message && (
        <div
          className={`px-4 py-2 text-[12px] border-b ${
            message.type === 'success'
              ? 'bg-[#1a1a1a] border-[#1e1e1e] text-[#e0e0e0]'
              : message.type === 'error'
              ? 'bg-[#1a1a1a] border-[#1e1e1e] text-[#999]'
              : 'bg-[#161616] border-[#1e1e1e] text-[#555]'
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Stats bar */}
      <div className="grid grid-cols-5 gap-px bg-[#1e1e1e] border-b border-[#1e1e1e]">
        {[
          { label: 'Entities', value: status?.total_entities ?? 0, icon: 'fa-cube' },
          { label: 'Relations', value: status?.total_relations ?? 0, icon: 'fa-link' },
          { label: 'Queries', value: stats?.total_queries ?? 0, icon: 'fa-magnifying-glass' },
          { label: 'Cycles', value: status?.cycle_count ?? 0, icon: 'fa-rotate' },
          { label: 'Avg Query', value: stats ? `${stats.avg_query_time_ms.toFixed(1)}ms` : '0.0ms', icon: 'fa-gauge-high' },
        ].map((m) => (
          <div key={m.label} className="bg-[#0d0d0d] px-3 py-2 flex flex-col gap-0.5">
            <div className="flex items-center gap-1.5 text-[10px] text-[#555] uppercase tracking-wide">
              <i className={`fa-solid ${m.icon} text-[9px]`} />
              {m.label}
            </div>
            <div className="text-[16px] font-bold text-[#e0e0e0]">{m.value}</div>
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-[#1e1e1e] bg-[#0d0d0d]">
        <button
          onClick={handleRunCycle}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded bg-[#1a1a1a] hover:bg-[#222] text-[#e0e0e0] border border-[#1e1e1e] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <i className="fa-solid fa-play text-[10px]" />
          Run Cycle
        </button>
        <button
          onClick={handleSimulate}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded bg-[#1a1a1a] hover:bg-[#222] text-[#e0e0e0] border border-[#1e1e1e] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <i className="fa-solid fa-forward text-[10px]" />
          Simulate
        </button>
        <button
          onClick={handleReset}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold rounded bg-[#161616] hover:bg-[#1a1a1a] text-[#999] border border-[#1e1e1e] disabled:opacity-40 disabled:cursor-not-allowed transition-colors ml-auto"
        >
          <i className="fa-solid fa-arrow-rotate-left text-[10px]" />
          Reset
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 text-[12px] bg-[#1a1a1a] border-b border-[#1e1e1e] text-[#999]">
          <i className="fa-solid fa-triangle-exclamation mr-1.5" />
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#1e1e1e] bg-[#0d0d0d]">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'bg-[#161616] text-[#e0e0e0] border-[#e0e0e0]'
                : 'text-[#555] hover:text-[#999] border-transparent'
            }`}
          >
            <i className={`fa-solid ${tab.icon} text-[11px]`} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-auto p-3">
        {/* TAB: Entities & Relations */}
        {activeTab === 'entities' && (
          <div className="flex flex-col gap-3">
            {/* Category distribution badges */}
            {Object.keys(categoryDist).length > 0 && (
              <div className="bg-[#161616] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <i className="fa-solid fa-tags text-[11px] text-[#999]" />
                  <span className="text-[12px] font-semibold">Category Distribution</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(categoryDist).map(([cat, count]) => (
                    <span
                      key={cat}
                      className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded bg-[#1a1a1a] text-[#999] border border-[#1e1e1e]"
                    >
                      {cat}
                      <span className="text-[#e0e0e0] font-bold">{count}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Entities list */}
            <div className="bg-[#161616] rounded-lg border border-[#1e1e1e] p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <i className="fa-solid fa-cube text-[11px] text-[#999]" />
                <span className="text-[12px] font-semibold">Entities</span>
                <span className="text-[10px] text-[#555]">({entities.length})</span>
              </div>
              {entities.length > 0 ? (
                <div className="flex flex-col gap-1.5">
                  {entities.map((entity) => (
                    <div
                      key={entity.entity_id}
                      className="bg-[#0d0d0d] rounded border border-[#1e1e1e] p-2"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-[12px] font-semibold text-[#e0e0e0] truncate">
                          {entity.name}
                        </span>
                        <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#999] border border-[#1e1e1e] shrink-0">
                          {entity.category}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-[10px] text-[#555]">
                        <span>
                          <i className="fa-solid fa-location-dot mr-1" />
                          {formatPosition(entity.position)}
                        </span>
                      </div>
                      {entity.tags && entity.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {entity.tags.map((tag) => (
                            <span
                              key={tag}
                              className="text-[9px] px-1.5 py-0.5 rounded bg-[#161616] text-[#555] border border-[#1e1e1e]"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-[11px] text-[#555] py-4">No entities indexed</div>
              )}
            </div>

            {/* Relations list */}
            <div className="bg-[#161616] rounded-lg border border-[#1e1e1e] p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <i className="fa-solid fa-link text-[11px] text-[#999]" />
                <span className="text-[12px] font-semibold">Relations</span>
                <span className="text-[10px] text-[#555]">({relations.length})</span>
              </div>
              {relations.length > 0 ? (
                <div className="flex flex-col gap-1.5">
                  {relations.map((rel) => {
                    const pct = Math.min(100, Math.max(0, rel.weight * 100));
                    return (
                      <div
                        key={rel.relation_id}
                        className="bg-[#0d0d0d] rounded border border-[#1e1e1e] p-2"
                      >
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#999] border border-[#1e1e1e]">
                            {rel.relation}
                          </span>
                          <span className="text-[10px] text-[#555] font-mono">
                            {(rel.weight * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 text-[11px] text-[#999] mb-1.5">
                          <span className="font-mono truncate">{rel.source_id}</span>
                          <i className="fa-solid fa-arrow-right text-[9px] text-[#555]" />
                          <span className="font-mono truncate">{rel.target_id}</span>
                        </div>
                        <div className="w-full h-1 bg-[#161616] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[#e0e0e0]"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center text-[11px] text-[#555] py-4">No relations indexed</div>
              )}
            </div>
          </div>
        )}

        {/* TAB: Query & Path (read-only query history) */}
        {activeTab === 'query' && (
          <div className="flex flex-col gap-2">
            <div className="bg-[#161616] rounded-lg border border-[#1e1e1e] p-3">
              <div className="flex items-center gap-1.5 mb-2">
                <i className="fa-solid fa-clock-rotate-left text-[11px] text-[#999]" />
                <span className="text-[12px] font-semibold">Recent Queries</span>
                <span className="text-[10px] text-[#555]">({queries.length})</span>
              </div>
              {queries.length > 0 ? (
                <div className="flex flex-col gap-1.5">
                  {queries.map((q) => (
                    <div
                      key={q.query_id}
                      className="bg-[#0d0d0d] rounded border border-[#1e1e1e] p-2"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-[11px] text-[#e0e0e0] font-mono truncate">
                          {q.query_text}
                        </span>
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#999] border border-[#1e1e1e] shrink-0">
                          {q.result_count} results
                        </span>
                      </div>
                      <div className="text-[10px] text-[#555]">{q.timestamp}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-[11px] text-[#555] py-4">No queries recorded</div>
              )}
            </div>
          </div>
        )}

        {/* TAB: History & Stats */}
        {activeTab === 'stats' && (
          <div className="flex flex-col gap-3">
            {/* Stat tiles */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Total Queries', value: stats?.total_queries ?? 0, icon: 'fa-magnifying-glass' },
                { label: 'Links Built', value: stats?.total_links_built ?? 0, icon: 'fa-link' },
                { label: 'Relations Decayed', value: stats?.total_relations_decayed ?? 0, icon: 'fa-arrow-down' },
                { label: 'Avg Query Time', value: stats ? `${stats.avg_query_time_ms.toFixed(2)}ms` : '0.00ms', icon: 'fa-gauge-high' },
              ].map((m) => (
                <div key={m.label} className="bg-[#161616] rounded-lg border border-[#1e1e1e] p-3">
                  <div className="flex items-center gap-1.5 text-[10px] text-[#555] uppercase tracking-wide mb-1">
                    <i className={`fa-solid ${m.icon} text-[9px]`} />
                    {m.label}
                  </div>
                  <div className="text-[18px] font-bold text-[#e0e0e0]">{m.value}</div>
                </div>
              ))}
            </div>

            {/* Relation distribution bars */}
            {Object.keys(relationDist).length > 0 && (
              <div className="bg-[#161616] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <i className="fa-solid fa-chart-simple text-[11px] text-[#999]" />
                  <span className="text-[12px] font-semibold">Relation Distribution</span>
                </div>
                <div className="flex flex-col gap-2">
                  {Object.entries(relationDist).map(([rel, count]) => (
                    <div key={rel} className="flex items-center gap-2">
                      <span className="text-[11px] text-[#999] w-28 truncate">{rel}</span>
                      <div className="flex-1 h-3 bg-[#0d0d0d] rounded-full overflow-hidden border border-[#1e1e1e]">
                        <div
                          className="h-full rounded-full bg-[#999]"
                          style={{ width: `${(count / maxRelationCount) * 100}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-[#555] font-mono w-8 text-right">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Category distribution badges */}
            {Object.keys(categoryDist).length > 0 && (
              <div className="bg-[#161616] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <i className="fa-solid fa-tags text-[11px] text-[#999]" />
                  <span className="text-[12px] font-semibold">Category Distribution</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(categoryDist).map(([cat, count]) => (
                    <span
                      key={cat}
                      className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded bg-[#1a1a1a] text-[#999] border border-[#1e1e1e]"
                    >
                      {cat}
                      <span className="text-[#e0e0e0] font-bold">{count}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Pending ingest info */}
            {status && (
              <div className="bg-[#161616] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-1.5 mb-2">
                  <i className="fa-solid fa-database text-[11px] text-[#999]" />
                  <span className="text-[12px] font-semibold">Index State</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="flex justify-between bg-[#0d0d0d] rounded px-2 py-1 border border-[#1e1e1e]">
                    <span className="text-[#555]">Pending Ingest</span>
                    <span className="text-[#e0e0e0] font-mono">{status.pending_ingest}</span>
                  </div>
                  <div className="flex justify-between bg-[#0d0d0d] rounded px-2 py-1 border border-[#1e1e1e]">
                    <span className="text-[#555]">Cycle Count</span>
                    <span className="text-[#e0e0e0] font-mono">{status.cycle_count}</span>
                  </div>
                </div>
              </div>
            )}

            {Object.keys(relationDist).length === 0 && Object.keys(categoryDist).length === 0 && !status && (
              <div className="text-center text-[11px] text-[#555] py-4">No stats available</div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-1.5 border-t border-[#1e1e1e] bg-[#0d0d0d] flex items-center justify-between text-[10px] text-[#555]">
        <span>
          <i className="fa-solid fa-circle-info mr-1" />
          Auto-refresh every 3s
        </span>
        <span>
          {status ? `${status.total_entities} ent · ${status.total_relations} rel` : 'Connecting'}
        </span>
      </div>
    </div>
  );
};

export default SemanticWorldIndexerPanel;
