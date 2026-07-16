import React, { useState, useEffect, useCallback } from 'react';
import { composerApi, toolchainApi } from '../utils/api';

type TabType = 'compositions' | 'chains' | 'templates';

const RELATION_COLORS: Record<string, string> = {
  depends_on: '#ef4444',
  implements: '#22c55e',
  extends: '#3b82f6',
  alternative_to: '#f59e0b',
  composed_of: '#8b5cf6',
  used_in: '#06b6d4',
};

const STATUS_COLORS: Record<string, string> = {
  draft: '#6b7280',
  ready: '#3b82f6',
  running: '#f59e0b',
  completed: '#22c55e',
  failed: '#ef4444',
  cancelled: '#9ca3af',
  paused: '#8b5cf6',
};

const CompositionGraph: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('compositions');
  const [compositions, setCompositions] = useState<any[]>([]);
  const [chains, setChains] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [executionPlan, setExecutionPlan] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [compRes, chainRes, tmplRes] = await Promise.all([
        composerApi.list(),
        toolchainApi.listChains(),
        toolchainApi.listTemplates(),
      ]);
      setCompositions((compRes as any)?.compositions || []);
      setChains((chainRes as any)?.chains || (chainRes as any) || []);
      setTemplates((tmplRes as any)?.templates || (tmplRes as any) || []);
    } catch (e) {
      // use empty defaults
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSelectComposition = async (id: string) => {
    try {
      const comp = await composerApi.get(id);
      setSelectedItem(comp);
      setExecutionPlan(null);
    } catch (e) { /* ignore */ }
  };

  const handleSelectChain = async (id: string) => {
    try {
      const chain = await toolchainApi.getChain(id);
      setSelectedItem(chain);
      const plan = await toolchainApi.resolveChain(id);
      setExecutionPlan(plan);
    } catch (e) { /* ignore */ }
  };

  const handleExecuteChain = async (id: string) => {
    try {
      await toolchainApi.executeChain(id);
      loadData();
    } catch (e) { /* ignore */ }
  };

  const handleCreateChain = async () => {
    try {
      await toolchainApi.createChain('New Chain', 'Auto-created chain');
      loadData();
    } catch (e) { /* ignore */ }
  };

  const renderCompositionGraph = () => {
    if (!selectedItem || !selectedItem.tasks) return null;

    const tasks = selectedItem.tasks || [];
    const channels = selectedItem.channels || [];
    const nodeWidth = 160;
    const nodeHeight = 60;
    const spacing = 200;

    return (
      <div className="relative bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-4 overflow-auto" style={{ minHeight: 300 }}>
        <svg width={Math.max(tasks.length * spacing + 100, 600)} height={400} className="block">
          {channels.map((ch: any, i: number) => {
            const sourceIdx = tasks.findIndex((t: any) => t.id === ch.source_task);
            const targetIdx = tasks.findIndex((t: any) => t.id === ch.target_task);
            if (sourceIdx < 0 || targetIdx < 0) return null;
            const x1 = 80 + sourceIdx * spacing + nodeWidth;
            const y1 = 200;
            const x2 = 80 + targetIdx * spacing;
            const y2 = 200;
            const midX = (x1 + x2) / 2;
            return (
              <g key={ch.id || i}>
                <path
                  d={`M ${x1} ${y1} C ${midX} ${y1 - 60}, ${midX} ${y2 - 60}, ${x2} ${y2}`}
                  fill="none"
                  stroke={RELATION_COLORS.composed_of}
                  strokeWidth={2}
                  strokeDasharray="6 3"
                  opacity={0.7}
                />
                <text x={midX} y={Math.min(y1, y2) - 30} textAnchor="middle" fill="#888" fontSize={10}>
                  {ch.name || ch.data_type || 'data'}
                </text>
              </g>
            );
          })}
          {tasks.map((task: any, i: number) => {
            const x = 80 + i * spacing;
            const y = 170;
            const taskColor = task.task_type === 'code' ? '#3b82f6' :
              task.task_type === 'art' ? '#8b5cf6' :
              task.task_type === 'test' ? '#22c55e' : '#f59e0b';
            return (
              <g key={task.id}>
                <rect x={x} y={y} width={nodeWidth} height={nodeHeight} rx={8}
                  fill="#1a1a1a" stroke={taskColor} strokeWidth={2} />
                <text x={x + nodeWidth / 2} y={y + 20} textAnchor="middle" fill="#e0e0e0" fontSize={12} fontWeight="bold">
                  {task.name?.substring(0, 16)}
                </text>
                <text x={x + nodeWidth / 2} y={y + 40} textAnchor="middle" fill={taskColor} fontSize={10}>
                  {task.task_type || task.agent_role || 'task'}
                </text>
                {task.dependencies && task.dependencies.map((depId: string) => {
                  const depIdx = tasks.findIndex((t: any) => t.id === depId);
                  if (depIdx < 0) return null;
                  const dx = 80 + depIdx * spacing + nodeWidth;
                  const dy = 200;
                  return (
                    <line key={depId} x1={dx} y1={dy} x2={x} y2={y + 30}
                      stroke="#ef4444" strokeWidth={1.5} opacity={0.5} />
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>
    );
  };

  const renderChainGraph = () => {
    if (!executionPlan) return null;

    const groups = executionPlan.execution_groups || [];
    const nodeWidth = 140;
    const nodeHeight = 50;

    return (
      <div className="relative bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-4 overflow-auto" style={{ minHeight: 300 }}>
        <svg width={Math.max(groups.length * 200 + 100, 600)} height={groups.length * 120 + 100} className="block">
          {groups.map((group: any, gi: number) => {
            const groupX = 60;
            const groupY = 40 + gi * 120;
            return (
              <g key={gi}>
                <rect x={groupX - 10} y={groupY - 10} width={group.parallel_steps.length * 170 + 20}
                  height={nodeHeight + 30} rx={6} fill="none" stroke="#333" strokeWidth={1} strokeDasharray="4 2" />
                <text x={groupX} y={groupY - 16} fill="#666" fontSize={10}>
                  Group {gi + 1} ({group.step_count} parallel)
                </text>
                {group.parallel_steps.map((step: any, si: number) => {
                  const sx = groupX + si * 170;
                  const sy = groupY;
                  const statusColor = STATUS_COLORS[step.status] || '#6b7280';
                  return (
                    <g key={step.id}>
                      <rect x={sx} y={sy} width={nodeWidth} height={nodeHeight} rx={6}
                        fill="#1a1a1a" stroke={statusColor} strokeWidth={2} />
                      <text x={sx + nodeWidth / 2} y={sy + 18} textAnchor="middle" fill="#e0e0e0" fontSize={11} fontWeight="bold">
                        {step.name?.substring(0, 14)}
                      </text>
                      <text x={sx + nodeWidth / 2} y={sy + 36} textAnchor="middle" fill={statusColor} fontSize={9}>
                        {step.tool_name || step.step_type}
                      </text>
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>
    );
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'compositions', label: 'Compositions', icon: 'fa-diagram-project' },
    { key: 'chains', label: 'Tool Chains', icon: 'fa-link' },
    { key: 'templates', label: 'Templates', icon: 'fa-copy' },
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
        <button
          onClick={handleCreateChain}
          className="flex items-center gap-1 px-3 py-1 bg-orange-500/15 text-orange-500 rounded text-[11px] hover:bg-orange-500/25 transition-colors"
        >
          <i className="fa-solid fa-plus text-[9px]" />
          New Chain
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-64 border-r border-[#1e1e1e] overflow-y-auto p-3">
          {loading ? (
            <div className="text-[#555] text-[11px] text-center py-8">Loading...</div>
          ) : activeTab === 'compositions' ? (
            compositions.map((comp: any) => (
              <div
                key={comp.id}
                onClick={() => handleSelectComposition(comp.id)}
                className={`p-2.5 rounded-lg mb-1.5 cursor-pointer transition-colors ${
                  selectedItem?.id === comp.id ? 'bg-orange-500/10 border border-orange-500/30' : 'bg-[#1a1a1a] hover:bg-[#222] border border-transparent'
                }`}
              >
                <div className="text-[12px] font-medium">{comp.name || comp.objective || 'Untitled'}</div>
                <div className="text-[10px] text-[#666] mt-0.5">
                  {comp.state || comp.status || 'draft'} · {comp.task_count || comp.step_count || 0} tasks
                </div>
              </div>
            ))
          ) : activeTab === 'chains' ? (
            chains.map((chain: any) => (
              <div
                key={chain.id}
                onClick={() => handleSelectChain(chain.id)}
                className={`p-2.5 rounded-lg mb-1.5 cursor-pointer transition-colors ${
                  selectedItem?.id === chain.id ? 'bg-orange-500/10 border border-orange-500/30' : 'bg-[#1a1a1a] hover:bg-[#222] border border-transparent'
                }`}
              >
                <div className="text-[12px] font-medium">{chain.name}</div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-[10px]" style={{ color: STATUS_COLORS[chain.status] || '#666' }}>{chain.status}</span>
                  <span className="text-[10px] text-[#555]">· {chain.step_count || 0} steps</span>
                </div>
              </div>
            ))
          ) : (
            templates.map((tmpl: any) => (
              <div key={tmpl.id} className="p-2.5 rounded-lg mb-1.5 bg-[#1a1a1a] border border-transparent">
                <div className="text-[12px] font-medium">{tmpl.name}</div>
                <div className="text-[10px] text-[#666] mt-0.5">
                  {tmpl.category} · {tmpl.step_definitions?.length || 0} steps
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {selectedItem ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-[14px] font-bold">{selectedItem.name}</h3>
                  <p className="text-[11px] text-[#888] mt-0.5">{selectedItem.description || selectedItem.objective || ''}</p>
                </div>
                {activeTab === 'chains' && selectedItem.status !== 'running' && (
                  <button
                    onClick={() => handleExecuteChain(selectedItem.id)}
                    className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded text-[11px] hover:bg-green-700 transition-colors"
                  >
                    <i className="fa-solid fa-play text-[9px]" />
                    Execute
                  </button>
                )}
              </div>

              {activeTab === 'compositions' && renderCompositionGraph()}
              {activeTab === 'chains' && renderChainGraph()}

              {(selectedItem.tasks || selectedItem.steps || []).length > 0 && (
                <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <h4 className="text-[12px] font-semibold text-[#999] mb-2">
                    {activeTab === 'compositions' ? 'Tasks' : 'Steps'} ({(selectedItem.tasks || selectedItem.steps || []).length})
                  </h4>
                  <div className="space-y-1">
                    {(selectedItem.tasks || selectedItem.steps || []).map((item: any, i: number) => (
                      <div key={item.id || i} className="flex items-center gap-2 p-2 bg-[#151515] rounded">
                        <div className="w-5 h-5 rounded-full bg-[#222] flex items-center justify-center text-[9px] text-[#888]">
                          {i + 1}
                        </div>
                        <div className="flex-1">
                          <span className="text-[11px]">{item.name}</span>
                          <span className="text-[10px] text-[#555] ml-2">{item.task_type || item.step_type || item.tool_name}</span>
                        </div>
                        <span className="text-[10px]" style={{ color: STATUS_COLORS[item.status] || '#666' }}>
                          {item.status || 'pending'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-[#555] text-[12px]">
              <div className="text-center">
                <i className="fa-solid fa-diagram-project text-[32px] mb-3 text-[#333]" />
                <p>Select an item to view its composition graph</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CompositionGraph;
