import React, { useState, useEffect, useCallback } from 'react';
import { knowledgeGraphApi } from '../utils/api';

type TabType = 'nodes' | 'patterns' | 'search';

const DOMAIN_COLORS: Record<string, string> = {
  game_design: '#f59e0b',
  code_pattern: '#3b82f6',
  architecture: '#22c55e',
  ai_behavior: '#ef4444',
  rendering: '#8b5cf6',
  physics: '#06b6d4',
  audio: '#ec4899',
  narrative: '#f97316',
  ui_ux: '#14b8a6',
  performance: '#eab308',
  tooling: '#6366f1',
  testing: '#84cc16',
};

const CONFIDENCE_BADGE: Record<string, { bg: string; text: string }> = {
  speculative: { bg: 'bg-gray-800', text: 'text-gray-400' },
  experimental: { bg: 'bg-blue-900/40', text: 'text-blue-400' },
  validated: { bg: 'bg-green-900/40', text: 'text-green-400' },
  proven: { bg: 'bg-yellow-900/40', text: 'text-yellow-400' },
  canonical: { bg: 'bg-orange-900/40', text: 'text-orange-400' },
};

const KnowledgeExplorer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('nodes');
  const [nodes, setNodes] = useState<any[]>([]);
  const [patterns, setPatterns] = useState<any[]>([]);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [relatedNodes, setRelatedNodes] = useState<any[]>([]);
  const [relations, setRelations] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterDomain, setFilterDomain] = useState('');
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadNodes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await knowledgeGraphApi.listNodes(filterDomain || undefined);
      setNodes((res as any)?.nodes || (res as any) || []);
    } catch (e) { /* ignore */ }
    setLoading(false);
  }, [filterDomain]);

  const loadPatterns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await knowledgeGraphApi.listPatterns();
      setPatterns((res as any)?.patterns || (res as any) || []);
    } catch (e) { /* ignore */ }
    setLoading(false);
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const res = await knowledgeGraphApi.stats();
      setStats(res);
    } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => {
    if (activeTab === 'nodes') loadNodes();
    else if (activeTab === 'patterns') loadPatterns();
    loadStats();
  }, [activeTab, loadNodes, loadPatterns, loadStats]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const res = await knowledgeGraphApi.search(searchQuery, filterDomain || undefined);
      setSearchResults((res as any)?.results || (res as any) || []);
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  const handleSelectNode = async (nodeId: string) => {
    try {
      const node = await knowledgeGraphApi.getNode(nodeId);
      setSelectedNode(node);
      const related = await knowledgeGraphApi.getRelated(nodeId);
      setRelatedNodes((related as any) || []);
      const rels = await knowledgeGraphApi.listRelations(nodeId);
      setRelations((rels as any)?.relations || (rels as any) || []);
    } catch (e) { /* ignore */ }
  };

  const handleCreateNode = async () => {
    try {
      await knowledgeGraphApi.addNode('New Knowledge Node', filterDomain || 'game_design');
      loadNodes();
    } catch (e) { /* ignore */ }
  };

  const renderNodeGraph = () => {
    if (!selectedNode) return null;

    const centerX = 300;
    const centerY = 200;
    const radius = 120;

    return (
      <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-4 overflow-auto" style={{ minHeight: 280 }}>
        <svg width={600} height={400} className="block mx-auto">
          {relatedNodes.map((rel: any, i: number) => {
            const angle = (2 * Math.PI * i) / relatedNodes.length - Math.PI / 2;
            const rx = centerX + radius * Math.cos(angle);
            const ry = centerY + radius * Math.sin(angle);
            const node = rel.node || rel;
            const domainColor = DOMAIN_COLORS[node.domain] || '#666';
            return (
              <g key={node.id || i}>
                <line x1={centerX} y1={centerY} x2={rx} y2={ry}
                  stroke="#333" strokeWidth={1} strokeDasharray="4 2" />
                <rect x={rx - 60} y={ry - 18} width={120} height={36} rx={6}
                  fill="#1a1a1a" stroke={domainColor} strokeWidth={1.5} />
                <text x={rx} y={ry - 2} textAnchor="middle" fill="#e0e0e0" fontSize={10} fontWeight="bold">
                  {(node.title || '').substring(0, 14)}
                </text>
                <text x={rx} y={ry + 12} textAnchor="middle" fill={domainColor} fontSize={8}>
                  {node.domain} · d={rel.distance || 1}
                </text>
              </g>
            );
          })}
          <circle cx={centerX} cy={centerY} r={40} fill="#1a1a1a"
            stroke={DOMAIN_COLORS[selectedNode.domain] || '#f59e0b'} strokeWidth={2} />
          <text x={centerX} y={centerY - 4} textAnchor="middle" fill="#e0e0e0" fontSize={10} fontWeight="bold">
            {(selectedNode.title || '').substring(0, 12)}
          </text>
          <text x={centerX} y={centerY + 10} textAnchor="middle"
            fill={DOMAIN_COLORS[selectedNode.domain] || '#f59e0b'} fontSize={8}>
            {selectedNode.domain}
          </text>
        </svg>
      </div>
    );
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'nodes', label: 'Knowledge Nodes', icon: 'fa-circle-nodes' },
    { key: 'patterns', label: 'Design Patterns', icon: 'fa-puzzle-piece' },
    { key: 'search', label: 'Search', icon: 'fa-magnifying-glass' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#111] text-[#e0e0e0]">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1e1e1e]">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] transition-colors ${
              activeTab === tab.key
                ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                : 'text-[#888] hover:text-[#ccc] hover:bg-[#1a1a1a]'
            }`}
          >
            <i className={`fa-solid ${tab.icon} text-[10px]`} />
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        {stats && (
          <div className="flex items-center gap-3 text-[10px] text-[#666]">
            <span>{stats.total_nodes || 0} nodes</span>
            <span>{stats.total_relations || 0} relations</span>
            <span>{stats.total_patterns || 0} patterns</span>
          </div>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-72 border-r border-[#1e1e1e] overflow-y-auto">
          {activeTab === 'search' && (
            <div className="p-3 border-b border-[#1e1e1e]">
              <div className="flex gap-1.5">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  placeholder="Search knowledge..."
                  className="flex-1 bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-[11px] text-[#e0e0e0] placeholder-[#555] focus:border-orange-500/50 focus:outline-none"
                />
                <button
                  onClick={handleSearch}
                  className="px-2.5 py-1.5 bg-orange-500/15 text-orange-500 rounded text-[11px] hover:bg-orange-500/25 transition-colors"
                >
                  <i className="fa-solid fa-magnifying-glass text-[10px]" />
                </button>
              </div>
              <select
                value={filterDomain}
                onChange={e => setFilterDomain(e.target.value)}
                className="w-full mt-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1 text-[10px] text-[#999] focus:outline-none"
              >
                <option value="">All Domains</option>
                {Object.keys(DOMAIN_COLORS).map(d => (
                  <option key={d} value={d}>{d.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
          )}

          <div className="p-2">
            {activeTab === 'nodes' && (
              <button
                onClick={handleCreateNode}
                className="w-full flex items-center gap-1.5 px-2.5 py-1.5 bg-orange-500/10 text-orange-500 rounded text-[10px] hover:bg-orange-500/20 transition-colors mb-2"
              >
                <i className="fa-solid fa-plus text-[8px]" />
                Add Node
              </button>
            )}

            {loading ? (
              <div className="text-[#555] text-[11px] text-center py-6">Loading...</div>
            ) : activeTab === 'nodes' ? (
              nodes.map((node: any) => {
                const domainColor = DOMAIN_COLORS[node.domain] || '#666';
                const conf = CONFIDENCE_BADGE[node.confidence] || CONFIDENCE_BADGE.experimental;
                return (
                  <div
                    key={node.id}
                    onClick={() => handleSelectNode(node.id)}
                    className={`p-2.5 rounded-lg mb-1 cursor-pointer transition-colors ${
                      selectedNode?.id === node.id ? 'bg-orange-500/10 border border-orange-500/30' : 'bg-[#1a1a1a] hover:bg-[#222] border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: domainColor }} />
                      <span className="text-[11px] font-medium flex-1 truncate">{node.title}</span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className={`text-[9px] px-1.5 py-0.5 rounded ${conf.bg} ${conf.text}`}>{node.confidence}</span>
                      <span className="text-[9px] text-[#555]">v{node.version}</span>
                    </div>
                  </div>
                );
              })
            ) : activeTab === 'patterns' ? (
              patterns.map((pattern: any) => (
                <div key={pattern.id} className="p-2.5 rounded-lg mb-1 bg-[#1a1a1a] border border-transparent">
                  <div className="text-[11px] font-medium">{pattern.name}</div>
                  <div className="text-[10px] text-[#666] mt-0.5">{pattern.category}</div>
                  <div className="text-[10px] text-[#555] mt-1 line-clamp-2">{pattern.problem}</div>
                </div>
              ))
            ) : (
              searchResults.map((result: any, i: number) => {
                const node = result.node || result;
                const domainColor = DOMAIN_COLORS[node.domain] || '#666';
                return (
                  <div
                    key={node.id || i}
                    onClick={() => handleSelectNode(node.id)}
                    className="p-2.5 rounded-lg mb-1 bg-[#1a1a1a] hover:bg-[#222] cursor-pointer border border-transparent"
                  >
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: domainColor }} />
                      <span className="text-[11px] font-medium">{node.title}</span>
                    </div>
                    <div className="text-[10px] text-[#555] mt-1 line-clamp-2">{node.content}</div>
                    {result.relevance_score !== undefined && (
                      <div className="text-[9px] text-orange-500 mt-1">
                        Relevance: {(result.relevance_score * 10).toFixed(1)}%
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {selectedNode ? (
            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: DOMAIN_COLORS[selectedNode.domain] || '#666' }} />
                  <h3 className="text-[14px] font-bold">{selectedNode.title}</h3>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] text-[#888]">{selectedNode.domain}</span>
                  {(() => {
                    const conf = CONFIDENCE_BADGE[selectedNode.confidence] || CONFIDENCE_BADGE.experimental;
                    return <span className={`text-[9px] px-1.5 py-0.5 rounded ${conf.bg} ${conf.text}`}>{selectedNode.confidence}</span>;
                  })()}
                  <span className="text-[10px] text-[#555]">v{selectedNode.version}</span>
                  <span className="text-[10px] text-[#555]">accessed {selectedNode.access_count || 0}×</span>
                </div>
              </div>

              <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                <h4 className="text-[11px] font-semibold text-[#999] mb-1.5">Content</h4>
                <p className="text-[12px] text-[#ccc] leading-relaxed">{selectedNode.content}</p>
              </div>

              {selectedNode.tags && selectedNode.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedNode.tags.map((tag: string) => (
                    <span key={tag} className="text-[9px] px-2 py-0.5 bg-[#1a1a1a] border border-[#2a2a2a] rounded text-[#888]">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {renderNodeGraph()}

              {relations.length > 0 && (
                <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <h4 className="text-[11px] font-semibold text-[#999] mb-2">Relations ({relations.length})</h4>
                  <div className="space-y-1">
                    {relations.map((rel: any, i: number) => (
                      <div key={rel.id || i} className="flex items-center gap-2 p-1.5 bg-[#151515] rounded text-[10px]">
                        <span className="text-[#888]">{rel.source_id}</span>
                        <span className="text-orange-500">{rel.relation_type}</span>
                        <span className="text-[#888]">{rel.target_id}</span>
                        {rel.description && <span className="text-[#555] ml-2">— {rel.description}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-[#555] text-[12px]">
              <div className="text-center">
                <i className="fa-solid fa-circle-nodes text-[32px] mb-3 text-[#333]" />
                <p>Select a knowledge node to explore</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default KnowledgeExplorer;
