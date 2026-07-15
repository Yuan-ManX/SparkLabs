import React, { useState, useEffect, useCallback } from 'react';
import { blockProgrammerApi, blockDeploymentApi } from '../utils/api';

interface BlockType {
  type_id: string;
  name: string;
  category: string;
  description: string;
  params: Array<{ name: string; param_type: string; default: string; description: string }>;
  returns: string;
  can_terminate: boolean;
}

interface BlockInstance {
  instance_id: string;
  type_id: string;
  category: string;
  name: string;
  params: Record<string, string>;
  order: number;
  enabled: boolean;
}

interface BlockProgram {
  program_id: string;
  name: string;
  description: string;
  blocks: BlockInstance[];
  status: string;
  created_at: string;
  updated_at: string;
  tags: string[];
}

interface ValidationReport {
  program_id: string;
  valid: boolean;
  findings: Array<{ severity: string; code: string; message: string; instance_id: string }>;
  validated_at: string;
}

interface TraceStep {
  step_index: number;
  kind: string;
  instance_id: string;
  block_name: string;
  detail: string;
  timestamp: string;
}

interface DryRunTrace {
  trace_id: string;
  program_id: string;
  steps: TraceStep[];
  completed: boolean;
  error: string;
  started_at: string;
  finished_at: string;
}

interface DeploymentStatus {
  pipeline: {
    composed: number;
    published: number;
    deployed: number;
    running: number;
  };
}

const CATEGORY_COLORS: Record<string, string> = {
  event: '#f59e0b',
  condition: '#3b82f6',
  action: '#22c55e',
  control: '#a855f7',
  variable: '#ec4899',
  operator: '#06b6d4',
  data: '#64748b',
};

const BlockProgrammerPanel: React.FC = () => {
  const [blockTypes, setBlockTypes] = useState<BlockType[]>([]);
  const [programs, setPrograms] = useState<BlockProgram[]>([]);
  const [selectedProgram, setSelectedProgram] = useState<BlockProgram | null>(null);
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [trace, setTrace] = useState<DryRunTrace | null>(null);
  const [deploymentStatus, setDeploymentStatus] = useState<DeploymentStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [newProgramName, setNewProgramName] = useState('');
  const [deployResult, setDeployResult] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [typesRes, programsRes, deployRes] = await Promise.all([
        blockProgrammerApi.listBlockTypes(),
        blockProgrammerApi.listPrograms(),
        blockDeploymentApi.status(),
      ]);
      setBlockTypes((typesRes as { data: BlockType[] }).data || []);
      setPrograms((programsRes as { data: BlockProgram[] }).data || []);
      setDeploymentStatus((deployRes as { data: DeploymentStatus }).data || null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const loadProgram = useCallback(async (programId: string) => {
    setLoading(true);
    setError('');
    try {
      const res = await blockProgrammerApi.getProgram(programId);
      setSelectedProgram((res as { data: BlockProgram }).data);
      setValidation(null);
      setTrace(null);
      setDeployResult('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load program');
    } finally {
      setLoading(false);
    }
  }, []);

  const createProgram = useCallback(async () => {
    if (!newProgramName.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await blockProgrammerApi.createProgram(newProgramName.trim());
      const program = (res as { data: BlockProgram }).data;
      setPrograms(prev => [...prev, program]);
      setSelectedProgram(program);
      setNewProgramName('');
      setValidation(null);
      setTrace(null);
      setDeployResult('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create program');
    } finally {
      setLoading(false);
    }
  }, [newProgramName]);

  const addBlock = useCallback(async (typeId: string) => {
    if (!selectedProgram || !typeId) return;
    setLoading(true);
    setError('');
    try {
      await blockProgrammerApi.addBlock(selectedProgram.program_id, typeId, {});
      await loadProgram(selectedProgram.program_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to add block');
    } finally {
      setLoading(false);
    }
  }, [selectedProgram, loadProgram]);

  const removeBlock = useCallback(async (instanceId: string) => {
    if (!selectedProgram) return;
    setLoading(true);
    setError('');
    try {
      await blockProgrammerApi.removeBlock(selectedProgram.program_id, instanceId);
      await loadProgram(selectedProgram.program_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to remove block');
    } finally {
      setLoading(false);
    }
  }, [selectedProgram, loadProgram]);

  const toggleBlock = useCallback(async (instanceId: string, enabled: boolean) => {
    if (!selectedProgram) return;
    try {
      await blockProgrammerApi.updateBlock(
        selectedProgram.program_id,
        instanceId,
        { enabled: !enabled }
      );
      await loadProgram(selectedProgram.program_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to toggle block');
    }
  }, [selectedProgram, loadProgram]);

  const validateProgram = useCallback(async () => {
    if (!selectedProgram) return;
    setLoading(true);
    setError('');
    try {
      const res = await blockProgrammerApi.validate(selectedProgram.program_id);
      setValidation((res as { data: ValidationReport }).data);
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation failed');
    } finally {
      setLoading(false);
    }
  }, [selectedProgram, loadData]);

  const dryRun = useCallback(async () => {
    if (!selectedProgram) return;
    setLoading(true);
    setError('');
    try {
      const res = await blockProgrammerApi.dryRun(selectedProgram.program_id, 200);
      setTrace((res as { data: DryRunTrace }).data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Dry run failed');
    } finally {
      setLoading(false);
    }
  }, [selectedProgram]);

  const publishProgram = useCallback(async () => {
    if (!selectedProgram) return;
    setLoading(true);
    setError('');
    try {
      await blockProgrammerApi.publish(selectedProgram.program_id);
      await loadProgram(selectedProgram.program_id);
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Publish failed');
    } finally {
      setLoading(false);
    }
  }, [selectedProgram, loadProgram, loadData]);

  const deployProgram = useCallback(async () => {
    if (!selectedProgram) return;
    setLoading(true);
    setError('');
    setDeployResult('');
    try {
      const res = await blockDeploymentApi.deploy(selectedProgram.program_id);
      const data = (res as { data: { runtime_id: string; bound_events: string[]; status: string } }).data;
      setDeployResult(`Deployed to runtime ${data.runtime_id}. Events bound: ${data.bound_events.join(', ') || 'none'}. Status: ${data.status}`);
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Deploy failed');
    } finally {
      setLoading(false);
    }
  }, [selectedProgram, loadData]);

  const groupedTypes = blockTypes.reduce((acc, bt) => {
    if (!acc[bt.category]) acc[bt.category] = [];
    acc[bt.category].push(bt);
    return acc;
  }, {} as Record<string, BlockType[]>);

  return (
    <div className="p-4 space-y-4 bg-[#0a0a0a] text-\[#eee\] min-h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-cyan-400">Block Programmer</h2>
        {deploymentStatus && (
          <div className="flex gap-3 text-xs">
            <span className="px-2 py-1 bg-[#0f0f0f] rounded">Composed: {deploymentStatus.pipeline.composed}</span>
            <span className="px-2 py-1 bg-[#0f0f0f] rounded">Published: {deploymentStatus.pipeline.published}</span>
            <span className="px-2 py-1 bg-[#0f0f0f] rounded">Deployed: {deploymentStatus.pipeline.deployed}</span>
            <span className="px-2 py-1 bg-green-900 rounded">Running: {deploymentStatus.pipeline.running}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-900 border border-red-700 rounded text-red-200 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-12 gap-4">
        {/* Left: Programs list */}
        <div className="col-span-3 space-y-3">
          <div className="bg-[#0f0f0f] rounded-lg p-3">
            <h3 className="text-sm font-semibold text-[#ccc] mb-2">Programs</h3>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={newProgramName}
                onChange={(e) => setNewProgramName(e.target.value)}
                placeholder="New program name"
                className="flex-1 px-2 py-1 text-xs bg-[#0a0a0a] border border-[#1e1e1e] rounded text-\[#eee\]"
              />
              <button
                onClick={createProgram}
                disabled={loading || !newProgramName.trim()}
                className="px-2 py-1 text-xs bg-cyan-600 hover:bg-cyan-700 rounded disabled:opacity-50"
              >
                Create
              </button>
            </div>
            <div className="space-y-1 max-h-96 overflow-y-auto">
              {programs.map(p => (
                <button
                  key={p.program_id}
                  onClick={() => loadProgram(p.program_id)}
                  className={`w-full text-left px-2 py-1.5 text-xs rounded ${
                    selectedProgram?.program_id === p.program_id
                      ? 'bg-cyan-900 text-cyan-200'
                      : 'bg-[#0a0a0a] hover:bg-[#1a1a1a]'
                  }`}
                >
                  <div className="font-medium truncate">{p.name}</div>
                  <div className="flex gap-2 text-[#666]">
                    <span>{p.blocks.length} blocks</span>
                    <span className={
                      p.status === 'published' ? 'text-green-400' :
                      p.status === 'validated' ? 'text-blue-400' :
                      p.status === 'invalid' ? 'text-red-400' :
                      'text-[#666]'
                    }>{p.status}</span>
                  </div>
                </button>
              ))}
              {programs.length === 0 && (
                <div className="text-xs text-[#666] py-4 text-center">No programs yet</div>
              )}
            </div>
          </div>
        </div>

        {/* Center: Program editor */}
        <div className="col-span-6 space-y-3">
          {selectedProgram ? (
            <>
              <div className="bg-[#0f0f0f] rounded-lg p-3">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-[#ccc]">{selectedProgram.name}</h3>
                  <div className="flex gap-1">
                    <button
                      onClick={validateProgram}
                      disabled={loading}
                      className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50"
                    >
                      Validate
                    </button>
                    <button
                      onClick={dryRun}
                      disabled={loading}
                      className="px-2 py-1 text-xs bg-purple-600 hover:bg-purple-700 rounded disabled:opacity-50"
                    >
                      Dry Run
                    </button>
                    <button
                      onClick={publishProgram}
                      disabled={loading}
                      className="px-2 py-1 text-xs bg-green-600 hover:bg-green-700 rounded disabled:opacity-50"
                    >
                      Publish
                    </button>
                    <button
                      onClick={deployProgram}
                      disabled={loading}
                      className="px-2 py-1 text-xs bg-orange-600 hover:bg-orange-700 rounded disabled:opacity-50"
                    >
                      Deploy
                    </button>
                  </div>
                </div>

                {deployResult && (
                  <div className="mb-2 p-2 bg-green-900 border border-green-700 rounded text-green-200 text-xs">
                    {deployResult}
                  </div>
                )}

                {/* Block stack */}
                <div className="space-y-1">
                  {selectedProgram.blocks.map((block, idx) => (
                    <div
                      key={block.instance_id}
                      className={`flex items-center gap-2 p-2 rounded ${
                        block.enabled ? 'bg-[#0a0a0a]' : 'bg-[#0a0a0a] opacity-50'
                      }`}
                    >
                      <span className="text-xs text-[#666] w-6">{idx}</span>
                      <span
                        className="w-2 h-8 rounded"
                        style={{ backgroundColor: CATEGORY_COLORS[block.category] || '#64748b' }}
                      />
                      <div className="flex-1">
                        <div className="text-xs font-medium text-\[#ddd\]">{block.name}</div>
                        <div className="text-xs text-[#666]">
                          {block.category} · {block.type_id}
                          {Object.keys(block.params).length > 0 && (
                            <span> · {Object.entries(block.params).map(([k, v]) => `${k}=${v}`).join(', ')}</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => toggleBlock(block.instance_id, block.enabled)}
                        className="text-xs text-[#999] hover:text-\[#ddd\]"
                      >
                        {block.enabled ? 'ON' : 'OFF'}
                      </button>
                      <button
                        onClick={() => removeBlock(block.instance_id)}
                        className="text-xs text-red-400 hover:text-red-300"
                      >
                        DEL
                      </button>
                    </div>
                  ))}
                  {selectedProgram.blocks.length === 0 && (
                    <div className="text-xs text-[#666] py-4 text-center">
                      No blocks. Add one from the palette.
                    </div>
                  )}
                </div>
              </div>

              {/* Validation results */}
              {validation && (
                <div className="bg-[#0f0f0f] rounded-lg p-3">
                  <h4 className="text-xs font-semibold text-[#ccc] mb-2">
                    Validation: {validation.valid ? 'VALID' : 'INVALID'}
                  </h4>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {validation.findings.map((f, i) => (
                      <div key={i} className={`text-xs p-1 rounded ${
                        f.severity === 'error' ? 'bg-red-900 text-red-200' :
                        f.severity === 'warning' ? 'bg-yellow-900 text-yellow-200' :
                        'bg-[#1a1a1a] text-[#ccc]'
                      }`}>
                        [{f.severity}] {f.code}: {f.message}
                      </div>
                    ))}
                    {validation.findings.length === 0 && (
                      <div className="text-xs text-green-400">No issues found</div>
                    )}
                  </div>
                </div>
              )}

              {/* Dry run trace */}
              {trace && (
                <div className="bg-[#0f0f0f] rounded-lg p-3">
                  <h4 className="text-xs font-semibold text-[#ccc] mb-2">
                    Dry Run: {trace.completed ? 'COMPLETED' : 'INCOMPLETE'}
                    {trace.error && <span className="text-red-400"> · {trace.error}</span>}
                  </h4>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {trace.steps.map((step, i) => (
                      <div key={i} className="text-xs p-1 bg-[#0a0a0a] rounded">
                        <span className="text-[#666]">[{step.step_index}]</span>{' '}
                        <span className="text-cyan-400">{step.kind}</span>{' '}
                        <span className="text-[#ccc]">{step.block_name}</span>{' '}
                        <span className="text-[#666]">{step.detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-[#0f0f0f] rounded-lg p-8 text-center text-[#666]">
              Select a program or create a new one
            </div>
          )}
        </div>

        {/* Right: Block type palette */}
        <div className="col-span-3">
          <div className="bg-[#0f0f0f] rounded-lg p-3 sticky top-4">
            <h3 className="text-sm font-semibold text-[#ccc] mb-2">Block Palette</h3>
            <div className="space-y-3 max-h-[600px] overflow-y-auto">
              {Object.entries(groupedTypes).map(([category, types]) => (
                <div key={category}>
                  <div className="text-xs font-semibold mb-1" style={{ color: CATEGORY_COLORS[category] || '#64748b' }}>
                    {category.toUpperCase()}
                  </div>
                  <div className="space-y-1">
                    {types.map(bt => (
                      <button
                        key={bt.type_id}
                        onClick={() => addBlock(bt.type_id)}
                        disabled={loading || !selectedProgram}
                        className="w-full text-left px-2 py-1 text-xs bg-[#0a0a0a] hover:bg-[#1a1a1a] rounded disabled:opacity-30 disabled:cursor-not-allowed"
                        title={bt.description}
                      >
                        <div className="font-medium text-\[#ddd\]">{bt.name}</div>
                        <div className="text-[#666] truncate">{bt.type_id}</div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlockProgrammerPanel;
