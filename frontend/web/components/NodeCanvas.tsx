import React, { useState, useCallback, useRef, useEffect } from 'react';
import { workflowSkillsApi, qualityGateApi, gameSkillApi } from '../utils/api';

interface NodeData {
  id: string;
  type: string;
  title: string;
  x: number;
  y: number;
  width: number;
  height: number;
  inputs: string[];
  outputs: string[];
  data: Record<string, unknown>;
  color: string;
}

interface ConnectionData {
  id: string;
  fromNode: string;
  fromPort: string;
  toNode: string;
  toPort: string;
}

const NODE_COLORS: Record<string, string> = {
  design: '#8b5cf6',
  development: '#3b82f6',
  review: '#f59e0b',
  testing: '#10b981',
  production: '#ef4444',
  creative: '#ec4899',
  orchestration: '#6366f1',
  quality: '#14b8a6',
  template: '#f97316',
  debug: '#64748b',
};

const CATEGORY_ICONS: Record<string, string> = {
  design: '🎨',
  development: '⚡',
  review: '🔍',
  testing: '🧪',
  production: '🚀',
  creative: '✨',
  orchestration: '🎯',
};

type NodeCanvasMode = 'workflows' | 'quality' | 'skills';

const NodeCanvas: React.FC = () => {
  const [mode, setMode] = useState<NodeCanvasMode>('workflows');
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [connections, setConnections] = useState<ConnectionData[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [_connecting, setConnecting] = useState<{ nodeId: string; port: string } | null>(null);
  const [_workflowSkills, setWorkflowSkills] = useState<any[]>([]);
  const [_qualityGates, setQualityGates] = useState<any[]>([]);
  const [_skillTemplates, setSkillTemplates] = useState<any[]>([]);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [qualityReport, setQualityReport] = useState<any>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (mode === 'workflows') {
      workflowSkillsApi.list().then((res: any) => {
        const skills = res.skills || [];
        setWorkflowSkills(skills);
        layoutWorkflowNodes(skills);
      }).catch(() => {});
    } else if (mode === 'quality') {
      qualityGateApi.gates().then((res: any) => {
        const gates = res.gates || [];
        setQualityGates(gates);
        layoutQualityNodes(gates);
      }).catch(() => {});
    } else if (mode === 'skills') {
      gameSkillApi.templates().then((res: any) => {
        const templates = res.templates || [];
        setSkillTemplates(templates);
        layoutSkillNodes(templates);
      }).catch(() => {});
    }
  }, [mode]);

  const layoutWorkflowNodes = (skills: any[]) => {
    const newNodes: NodeData[] = [];
    const cols = 4;
    const nodeW = 180;
    const nodeH = 100;
    const gapX = 220;
    const gapY = 130;

    skills.forEach((skill, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const cat = skill.category || 'development';
      newNodes.push({
        id: skill.id,
        type: cat,
        title: skill.display_name || skill.name,
        x: 40 + col * gapX,
        y: 40 + row * gapY,
        width: nodeW,
        height: nodeH,
        inputs: skill.quality_gates || [],
        outputs: skill.outputs || [],
        data: skill,
        color: NODE_COLORS[cat] || '#3b82f6',
      });
    });
    setNodes(newNodes);
    setConnections([]);
  };

  const layoutQualityNodes = (gates: any[]) => {
    const newNodes: NodeData[] = [];
    const cols = 3;
    const nodeW = 180;
    const nodeH = 90;
    const gapX = 220;
    const gapY = 120;

    gates.forEach((gate, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const _cat = gate.category || 'build_health';
      newNodes.push({
        id: gate.id,
        type: 'quality',
        title: gate.name,
        x: 40 + col * gapX,
        y: 40 + row * gapY,
        width: nodeW,
        height: nodeH,
        inputs: [],
        outputs: [gate.phase],
        data: gate,
        color: NODE_COLORS.quality,
      });
    });
    setNodes(newNodes);
    setConnections([]);
  };

  const layoutSkillNodes = (templates: any[]) => {
    const newNodes: NodeData[] = [];
    const cols = 4;
    const nodeW = 160;
    const nodeH = 80;
    const gapX = 200;
    const gapY = 110;

    templates.forEach((t, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const _cat = t.category || 'genre';
      newNodes.push({
        id: t.id,
        type: _cat === 'genre' ? 'template' : 'debug',
        title: t.name,
        x: 40 + col * gapX,
        y: 40 + row * gapY,
        width: nodeW,
        height: nodeH,
        inputs: [],
        outputs: t.tags || [],
        data: t,
        color: _cat === 'genre' ? NODE_COLORS.template : NODE_COLORS.debug,
      });
    });
    setNodes(newNodes);
    setConnections([]);
  };

  const handleMouseDown = useCallback((e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return;
    setDragging(nodeId);
    setSelectedNode(nodeId);
    const rect = canvasRef.current?.getBoundingClientRect();
    if (rect) {
      setDragOffset({
        x: e.clientX - rect.left - node.x,
        y: e.clientY - rect.top - node.y,
      });
    }
  }, [nodes]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left - dragOffset.x;
    const y = e.clientY - rect.top - dragOffset.y;
    setNodes(prev => prev.map(n => n.id === dragging ? { ...n, x, y } : n));
  }, [dragging, dragOffset]);

  const handleMouseUp = useCallback(() => {
    setDragging(null);
  }, []);

  const handleCanvasClick = useCallback(() => {
    setSelectedNode(null);
    setConnecting(null);
  }, []);

  const handleExecuteWorkflow = useCallback(async (skillId: string) => {
    try {
      const res: any = await workflowSkillsApi.execute(skillId, { concept: 'test' });
      setExecutionResult(res);
    } catch (e: any) {
      setExecutionResult({ error: e.message });
    }
  }, []);

  const handleEvaluateAll = useCallback(async () => {
    try {
      const res: any = await qualityGateApi.evaluateAll();
      setQualityReport(res);
    } catch (e: any) {
      setQualityReport({ error: e.message });
    }
  }, []);

  const selectedNodeData = nodes.find(n => n.id === selectedNode);

  const renderNode = (node: NodeData) => {
    const isSelected = selectedNode === node.id;
    return (
      <div
        key={node.id}
        onMouseDown={(e) => handleMouseDown(e, node.id)}
        className="absolute cursor-grab active:cursor-grabbing select-none"
        style={{ left: node.x, top: node.y, width: node.width }}
      >
        <div
          className={`rounded-lg border-2 transition-shadow ${
            isSelected ? 'shadow-lg shadow-blue-500/30 border-blue-400' : 'border-[#333] hover:border-[#555]'
          }`}
          style={{ backgroundColor: '#1a1a2e' }}
        >
          <div
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-t-md text-[10px] font-bold text-white"
            style={{ backgroundColor: node.color + 'cc' }}
          >
            <span>{CATEGORY_ICONS[node.type] || '📦'}</span>
            <span className="truncate">{node.title}</span>
          </div>
          <div className="px-2.5 py-2 space-y-1">
            {node.inputs.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {node.inputs.slice(0, 3).map((inp, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-blue-400 border border-blue-300" />
                    <span className="text-[8px] text-[#888] truncate max-w-[60px]">{inp}</span>
                  </div>
                ))}
              </div>
            )}
            {node.outputs.length > 0 && (
              <div className="flex flex-wrap gap-1 justify-end">
                {node.outputs.slice(0, 3).map((out, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <span className="text-[8px] text-[#888] truncate max-w-[60px]">{out}</span>
                    <div className="w-2 h-2 rounded-full bg-green-400 border border-green-300" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderDetailPanel = () => {
    if (!selectedNodeData) return null;
    const data = selectedNodeData.data as any;

    return (
      <div className="w-72 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded" style={{ backgroundColor: selectedNodeData.color }} />
          <span className="text-[12px] font-bold text-[#ccc]">{selectedNodeData.title}</span>
        </div>

        {data.description && (
          <div className="text-[10px] text-[#888]">{data.description}</div>
        )}

        {mode === 'workflows' && (
          <>
            <div className="space-y-1">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Steps</div>
              {(data.steps || []).map((step: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-[10px] p-1.5 bg-[#1a1a1a] rounded border border-[#333]">
                  <span className="text-[#555] w-4 text-center">{i + 1}</span>
                  <span className="text-[#ccc]">{step.name}</span>
                  {step.agent_role && <span className="text-[#666] ml-auto text-[8px]">{step.agent_role}</span>}
                </div>
              ))}
            </div>

            {data.slash_command && (
              <div className="space-y-1">
                <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Command</div>
                <div className="text-[11px] px-2 py-1 bg-[#1a1a1a] rounded border border-[#333] text-blue-400 font-mono">
                  {data.slash_command}
                </div>
              </div>
            )}

            <button
              onClick={() => handleExecuteWorkflow(selectedNodeData.id)}
              className="w-full py-1.5 bg-gradient-to-r from-orange-600 to-orange-500 text-white text-[10px] rounded font-medium"
            >
              Execute Workflow
            </button>

            {executionResult && (
              <div className="space-y-1">
                <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Result</div>
                <div className={`text-[10px] p-2 rounded border ${
                  executionResult.status === 'completed' ? 'bg-green-500/10 border-green-500/30 text-green-400' :
                  executionResult.error ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                  'bg-[#1a1a1a] border-[#333] text-[#ccc]'
                }`}>
                  {executionResult.error || `Status: ${executionResult.status} | Steps: ${executionResult.current_step + 1}/${executionResult.total_steps}`}
                </div>
              </div>
            )}
          </>
        )}

        {mode === 'quality' && (
          <>
            <div className="space-y-1">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Checks</div>
              <div className="text-[10px] text-[#aaa]">{data.check_count} checks</div>
            </div>
            <div className="space-y-1">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Threshold</div>
              <div className="text-[10px] text-[#aaa]">{((data.pass_threshold || 0) * 100).toFixed(0)}% pass rate</div>
            </div>
            <div className="space-y-1">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Phase</div>
              <div className="text-[10px] px-2 py-0.5 bg-[#1a1a1a] rounded border border-[#333] text-[#ccc]">
                {data.phase}
              </div>
            </div>
          </>
        )}

        {mode === 'skills' && (
          <>
            <div className="space-y-1">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Genre</div>
              <div className="text-[10px] text-[#ccc]">{data.genre}</div>
            </div>
            <div className="space-y-1">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Maturity</div>
              <div className={`text-[10px] px-2 py-0.5 rounded inline-block ${
                data.maturity === 'core' ? 'bg-green-500/20 text-green-400' :
                data.maturity === 'proven' ? 'bg-blue-500/20 text-blue-400' :
                data.maturity === 'validated' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-\[#f5f5f5\]0/20 text-[#999]'
              }`}>
                {data.maturity}
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Success Rate</div>
              <div className="w-full bg-[#1a1a1a] rounded-full h-1.5">
                <div
                  className="h-1.5 rounded-full bg-green-500"
                  style={{ width: `${(data.success_rate || 0) * 100}%` }}
                />
              </div>
              <div className="text-[9px] text-[#666]">{((data.success_rate || 0) * 100).toFixed(0)}% ({data.usage_count || 0} uses)</div>
            </div>
            {data.tags && data.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {data.tags.map((tag: string) => (
                  <span key={tag} className="text-[8px] px-1.5 py-0.5 bg-[#1a1a1a] text-[#888] rounded border border-[#333]">{tag}</span>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="flex items-center justify-between border-b border-[#1e1e1e] px-3 py-2">
        <div className="flex gap-1">
          {([
            { id: 'workflows' as NodeCanvasMode, label: 'Workflows', icon: '🔄' },
            { id: 'quality' as NodeCanvasMode, label: 'Quality Gates', icon: '✅' },
            { id: 'skills' as NodeCanvasMode, label: 'Skill Templates', icon: '⚒' },
          ]).map(tab => (
            <button
              key={tab.id}
              onClick={() => setMode(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] rounded transition-colors ${
                mode === tab.id
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : 'text-[#666] hover:text-[#999] hover:bg-[#151515] border border-transparent'
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {mode === 'quality' && (
          <button
            onClick={handleEvaluateAll}
            className="px-3 py-1.5 bg-gradient-to-r from-green-600 to-green-500 text-white text-[10px] rounded font-medium"
          >
            Evaluate All
          </button>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div
          ref={canvasRef}
          className="flex-1 relative overflow-hidden"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onClick={handleCanvasClick}
          style={{
            backgroundImage: 'radial-gradient(circle, #1a1a1a 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        >
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
            {connections.map(conn => {
              const from = nodes.find(n => n.id === conn.fromNode);
              const to = nodes.find(n => n.id === conn.toNode);
              if (!from || !to) return null;
              const x1 = from.x + from.width;
              const y1 = from.y + from.height / 2;
              const x2 = to.x;
              const y2 = to.y + to.height / 2;
              const cx1 = x1 + Math.abs(x2 - x1) * 0.5;
              const cx2 = x2 - Math.abs(x2 - x1) * 0.5;
              return (
                <path
                  key={conn.id}
                  d={`M ${x1} ${y1} C ${cx1} ${y1}, ${cx2} ${y2}, ${x2} ${y2}`}
                  fill="none"
                  stroke="#444"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                />
              );
            })}
          </svg>

          <div style={{ zIndex: 2 }}>
            {nodes.map(renderNode)}
          </div>

          {nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-[#555] text-[12px]">
              Loading {mode}...
            </div>
          )}
        </div>

        {renderDetailPanel()}
      </div>

      {qualityReport && (
        <div className="border-t border-[#1e1e1e] p-3 bg-[#0a0a0a]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-[#ccc]">Quality Assessment</span>
            <button onClick={() => setQualityReport(null)} className="text-[10px] text-[#666] hover:text-[#999]">✕</button>
          </div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-[#666]">Verdict:</span>
              <span className={`text-[10px] font-bold ${
                qualityReport.overall_verdict === 'pass' ? 'text-green-400' :
                qualityReport.overall_verdict === 'warning' ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {qualityReport.overall_verdict?.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-[#666]">Score:</span>
              <span className="text-[10px] text-[#ccc]">{((qualityReport.overall_score || 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-[#666]">Checks:</span>
              <span className="text-[10px] text-green-400">{qualityReport.total_pass}✓</span>
              <span className="text-[10px] text-red-400">{qualityReport.total_fail}✗</span>
              <span className="text-[10px] text-yellow-400">{qualityReport.total_warning}⚠</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NodeCanvas;
