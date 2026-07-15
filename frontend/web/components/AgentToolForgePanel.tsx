import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type ToolStatus = 'active' | 'development' | 'deprecated' | 'testing';
type SchemaFormat = 'openapi' | 'json_schema' | 'custom';

interface AgentTool {
  id: string;
  name: string;
  description: string;
  status: ToolStatus;
  schema_format: SchemaFormat;
  version: string;
  execution_count: number;
  last_executed: string;
  avg_latency_ms: number;
}

interface ToolSchema {
  id: string;
  tool_name: string;
  format: SchemaFormat;
  parameters: Record<string, any>;
  returns: Record<string, any>;
  created_at: string;
}

interface ExecutionRecord {
  id: string;
  tool_id: string;
  tool_name: string;
  status: 'success' | 'failure' | 'pending';
  latency_ms: number;
  input_preview: string;
  output_preview: string;
  timestamp: number;
}

interface PerformanceStats {
  total_executions: number;
  success_rate: number;
  avg_latency: number;
  p95_latency: number;
  p99_latency: number;
  active_tools: number;
  deprecated_tools: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const TOOL_STATUS_COLORS: Record<ToolStatus, string> = {
  active: '#6bcb77',
  development: '#fdcb6e',
  deprecated: '#888',
  testing: '#74b9ff',
};

const TOOL_STATUS_LABELS: Record<ToolStatus, string> = {
  active: 'Active',
  development: 'Dev',
  deprecated: 'Deprecated',
  testing: 'Testing',
};

const SCHEMA_COLORS: Record<SchemaFormat, string> = {
  openapi: '#6bcb77',
  json_schema: '#74b9ff',
  custom: '#a29bfe',
};

const SCHEMA_LABELS: Record<SchemaFormat, string> = {
  openapi: 'OpenAPI',
  json_schema: 'JSON Schema',
  custom: 'Custom',
};

const EXECUTION_STATUS_COLORS: Record<string, string> = {
  success: '#6bcb77',
  failure: '#ff6b6b',
  pending: '#fdcb6e',
};

const AgentToolForgePanel: React.FC = () => {
  const [tools, setTools] = useState<AgentTool[]>([]);
  const [schemas, setSchemas] = useState<ToolSchema[]>([]);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [performance, setPerformance] = useState<PerformanceStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);

  const apiBase = API_ROOT + '/agent';

  const defaultTools: AgentTool[] = [
    { id: uid(), name: 'DamageCalculator', description: 'Calculates combat damage with modifiers and resistances', status: 'active', schema_format: 'json_schema', version: '2.1.0', execution_count: 4523, last_executed: '15s ago', avg_latency_ms: 12 },
    { id: uid(), name: 'QuestValidator', description: 'Validates quest logic, prerequisites, and reward balance', status: 'active', schema_format: 'openapi', version: '1.3.2', execution_count: 2187, last_executed: '42s ago', avg_latency_ms: 34 },
    { id: uid(), name: 'LootGenerator', description: 'Procedurally generates loot tables based on level and biome', status: 'testing', schema_format: 'custom', version: '0.9.1', execution_count: 876, last_executed: '2m ago', avg_latency_ms: 8 },
    { id: uid(), name: 'DialogueCompiler', description: 'Compiles dialogue trees into optimized runtime format', status: 'development', schema_format: 'json_schema', version: '0.5.0', execution_count: 342, last_executed: '8m ago', avg_latency_ms: 56 },
    { id: uid(), name: 'BalanceProfiler', description: 'Profiles game economy and balance parameters', status: 'deprecated', schema_format: 'openapi', version: '0.8.0', execution_count: 1204, last_executed: '2d ago', avg_latency_ms: 45 },
    { id: uid(), name: 'NPCBehaviorSim', description: 'Simulates NPC behavior patterns for validation', status: 'active', schema_format: 'custom', version: '1.0.0', execution_count: 3098, last_executed: '5s ago', avg_latency_ms: 22 },
  ];

  const defaultSchemas: ToolSchema[] = [
    { id: uid(), tool_name: 'DamageCalculator', format: 'json_schema', parameters: { attack: 'number', defense: 'number', element: 'string' }, returns: { damage: 'number', critical: 'boolean' }, created_at: '1h ago' },
    { id: uid(), tool_name: 'QuestValidator', format: 'openapi', parameters: { quest_id: 'string', flags: 'array' }, returns: { valid: 'boolean', issues: 'array' }, created_at: '3h ago' },
    { id: uid(), tool_name: 'LootGenerator', format: 'custom', parameters: { level: 'number', biome: 'string', rarity: 'string' }, returns: { items: 'array', gold: 'number' }, created_at: '5h ago' },
  ];

  const defaultExecutions: ExecutionRecord[] = [
    { id: uid(), tool_id: 'tool-1', tool_name: 'DamageCalculator', status: 'success', latency_ms: 11, input_preview: '{ "attack": 45, "defense": 20... }', output_preview: '{ "damage": 32, "critical": false }', timestamp: Date.now() - 15000 },
    { id: uid(), tool_id: 'tool-1', tool_name: 'DamageCalculator', status: 'success', latency_ms: 14, input_preview: '{ "attack": 78, "defense": 12... }', output_preview: '{ "damage": 112, "critical": true }', timestamp: Date.now() - 30000 },
    { id: uid(), tool_id: 'tool-3', tool_name: 'LootGenerator', status: 'failure', latency_ms: 250, input_preview: '{ "level": -1, "biome": null }', output_preview: '{ "error": "Invalid input" }', timestamp: Date.now() - 60000 },
    { id: uid(), tool_id: 'tool-6', tool_name: 'NPCBehaviorSim', status: 'success', latency_ms: 18, input_preview: '{ "npc_id": "guard_07"... }', output_preview: '{ "path": [...], "state": "patrol" }', timestamp: Date.now() - 5000 },
    { id: uid(), tool_id: 'tool-2', tool_name: 'QuestValidator', status: 'pending', latency_ms: 0, input_preview: '{ "quest_id": "main_q12"... }', output_preview: '...', timestamp: Date.now() },
  ];

  const defaultPerformance: PerformanceStats = {
    total_executions: 12230,
    success_rate: 96.4,
    avg_latency: 18.5,
    p95_latency: 45,
    p99_latency: 120,
    active_tools: 3,
    deprecated_tools: 1,
  };

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/tool-forge/stats`);
      const data = await res.json();
      if (data.tools) setTools(data.tools);
      if (data.performance) setPerformance(data.performance);
    } catch {}
  }, []);

  const fetchTools = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/tool-forge/list-tools`);
      const data = await res.json();
      if (data.tools) setTools(data.tools);
    } catch {}
  }, []);

  const fetchPerformance = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/tool-forge/tool-performance`);
      const data = await res.json();
      setPerformance(data);
    } catch {}
  }, []);

  useEffect(() => {
    setTools(defaultTools);
    setSchemas(defaultSchemas);
    setExecutions(defaultExecutions);
    setPerformance(defaultPerformance);
    fetchStats();
    fetchTools();
    fetchPerformance();
  }, [fetchStats, fetchTools, fetchPerformance]);

  const handleDefineSchema = async () => {
    try {
      await fetch(`${apiBase}/tool-forge/define-schema`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_name: 'NewTool',
          format: 'json_schema',
          parameters: { input: 'string' },
          returns: { output: 'object' },
        }),
      });
      showMessage('Schema defined successfully', 'success');
      fetchStats();
    } catch {
      const newSchema: ToolSchema = {
        id: uid(),
        tool_name: `NewTool_${schemas.length + 1}`,
        format: 'json_schema',
        parameters: { input: 'string', options: 'object' },
        returns: { output: 'object', status: 'string' },
        created_at: 'just now',
      };
      setSchemas(prev => [...prev, newSchema]);
      showMessage('Schema defined (offline fallback)', 'info');
    }
  };

  const handleForgeTool = async () => {
    try {
      await fetch(`${apiBase}/tool-forge/forge-tool`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `ForgedTool_${tools.length + 1}`,
          description: 'A newly forged agent tool.',
          schema_format: 'json_schema',
        }),
      });
      showMessage('Tool forged successfully', 'success');
      fetchStats();
      fetchTools();
    } catch {
      const newTool: AgentTool = {
        id: uid(),
        name: `ForgedTool_${tools.length + 1}`,
        description: 'A newly forged agent tool.',
        status: 'development',
        schema_format: 'json_schema',
        version: '0.1.0',
        execution_count: 0,
        last_executed: 'never',
        avg_latency_ms: 0,
      };
      setTools(prev => [...prev, newTool]);
      showMessage('Tool forged (offline fallback)', 'info');
    }
  };

  const handleValidate = async () => {
    if (!selectedTool) {
      showMessage('Select a tool to validate first', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/tool-forge/validate-tool`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_id: selectedTool }),
      });
      showMessage('Tool validated successfully', 'success');
      fetchStats();
    } catch {
      showMessage('Tool validated (offline fallback)', 'info');
    }
  };

  const handleActivate = async () => {
    if (!selectedTool) {
      showMessage('Select a tool to activate first', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/tool-forge/activate-tool`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_id: selectedTool }),
      });
      setTools(prev => prev.map(t => t.id === selectedTool ? { ...t, status: 'active' as ToolStatus } : t));
      showMessage('Tool activated', 'success');
    } catch {
      setTools(prev => prev.map(t => t.id === selectedTool ? { ...t, status: 'active' as ToolStatus } : t));
      showMessage('Tool activated (offline fallback)', 'info');
    }
  };

  const handleDeprecate = async () => {
    if (!selectedTool) {
      showMessage('Select a tool to deprecate first', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/tool-forge/deprecate-tool`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_id: selectedTool }),
      });
      setTools(prev => prev.map(t => t.id === selectedTool ? { ...t, status: 'deprecated' as ToolStatus } : t));
      showMessage('Tool deprecated', 'info');
    } catch {
      setTools(prev => prev.map(t => t.id === selectedTool ? { ...t, status: 'deprecated' as ToolStatus } : t));
      showMessage('Tool deprecated (offline fallback)', 'info');
    }
  };

  const handleExecute = async () => {
    if (!selectedTool) {
      showMessage('Select a tool to execute first', 'error');
      return;
    }
    const tool = tools.find(t => t.id === selectedTool);
    try {
      await fetch(`${apiBase}/tool-forge/execut-tool`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tool_id: selectedTool, parameters: {} }),
      });
      showMessage(`Executed ${tool?.name || 'tool'}`, 'success');
      fetchStats();
      fetchPerformance();
    } catch {
      const newExec: ExecutionRecord = {
        id: uid(),
        tool_id: selectedTool,
        tool_name: tool?.name || 'Unknown',
        status: Math.random() > 0.2 ? 'success' : 'failure',
        latency_ms: Math.floor(Math.random() * 80) + 5,
        input_preview: '{ ... }',
        output_preview: '{ "result": "completed" }',
        timestamp: Date.now(),
      };
      setExecutions(prev => [newExec, ...prev].slice(0, 50));
      if (tool) {
        setTools(prev => prev.map(t => t.id === selectedTool ? { ...t, execution_count: t.execution_count + 1, avg_latency_ms: Math.floor((t.avg_latency_ms + newExec.latency_ms) / 2) } : t));
      }
      showMessage(`Executed ${tool?.name || 'tool'} (offline fallback)`, 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const activeCount = tools.filter(t => t.status === 'active').length;

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
          <span style={{ fontSize: 18 }}>🔨</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Tool Forge</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {performance && (
            <span style={{ fontSize: 10, color: '#888' }}>
              <span style={{ fontSize: 12, marginRight: 4 }}>🛠️</span>
              {activeCount} active · {performance.total_executions.toLocaleString()} runs
            </span>
          )}
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

      <div style={{ padding: '10px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <button onClick={handleDefineSchema} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#3a2d3a', color: '#a29bfe',
          border: '1px solid #4a3d4a', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>📐</span>Define Schema
        </button>
        <button onClick={handleForgeTool} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#4a3d2d', color: '#fdcb6e',
          border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>🔨</span>Forge Tool
        </button>
        <button onClick={handleValidate} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#2d3a4a', color: '#74b9ff',
          border: '1px solid #3d4a5a', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>📐</span>Validate
        </button>
        <button onClick={handleActivate} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#2d4a2d', color: '#6bcb77',
          border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>🛠️</span>Activate
        </button>
        <button onClick={handleDeprecate} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#3a1a1a', color: '#ff6b6b',
          border: '1px solid #5a2d2d', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>🔨</span>Deprecate
        </button>
        <button onClick={handleExecute} style={{
          padding: '6px 12px', fontSize: 11, fontWeight: 600,
          backgroundColor: '#4a2d2d', color: '#ff9f43',
          border: '1px solid #5a3d3d', borderRadius: 4, cursor: 'pointer',
        }}>
          <span style={{ marginRight: 4 }}>🛠️</span>Execute
        </button>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{
          width: 340, borderRight: '1px solid #2a2a3e',
          overflow: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>🛠️</span>Tool Registry
            <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({tools.length})</span>
          </div>

          {tools.map(tool => (
            <div key={tool.id} style={{
              padding: 10, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
              borderLeft: `3px solid ${TOOL_STATUS_COLORS[tool.status]}`,
              cursor: 'pointer',
              opacity: selectedTool === tool.id ? 1 : 0.85,
              boxShadow: selectedTool === tool.id ? '0 0 8px rgba(108, 92, 231, 0.3)' : 'none',
            }} onClick={() => setSelectedTool(selectedTool === tool.id ? null : tool.id)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 14 }}>🛠️</span>
                  <span style={{ fontWeight: 600, fontSize: 12 }}>{tool.name}</span>
                </div>
                <span style={{
                  fontSize: 9, padding: '2px 6px', borderRadius: 3,
                  backgroundColor: TOOL_STATUS_COLORS[tool.status] + '33',
                  color: TOOL_STATUS_COLORS[tool.status], fontWeight: 600,
                }}>
                  {TOOL_STATUS_LABELS[tool.status]}
                </span>
              </div>
              <div style={{ fontSize: 10, color: '#888', marginBottom: 4, lineHeight: 1.4 }}>
                {tool.description}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 10, color: '#666' }}>
                <div style={{ display: 'flex', gap: 8 }}>
                  <span>v{tool.version}</span>
                  <span style={{
                    padding: '1px 4px', borderRadius: 2,
                    backgroundColor: SCHEMA_COLORS[tool.schema_format] + '33',
                    color: SCHEMA_COLORS[tool.schema_format],
                  }}>
                    {SCHEMA_LABELS[tool.schema_format]}
                  </span>
                </div>
                <span>{tool.execution_count.toLocaleString()} runs</span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              padding: 14, backgroundColor: '#22223a', borderRadius: 8,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>📐</span>Schemas
                <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({schemas.length})</span>
              </div>
              {schemas.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {schemas.map(schema => (
                    <div key={schema.id} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 11 }}>{schema.tool_name}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 5px', borderRadius: 3,
                          backgroundColor: SCHEMA_COLORS[schema.format] + '33',
                          color: SCHEMA_COLORS[schema.format], fontWeight: 600,
                        }}>
                          {SCHEMA_LABELS[schema.format]}
                        </span>
                      </div>
                      <div style={{ fontSize: 10, color: '#888' }}>
                        <div>Params: {Object.keys(schema.parameters).join(', ')}</div>
                        <div>Returns: {Object.keys(schema.returns).join(', ')}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  textAlign: 'center', padding: 20, color: '#555',
                  backgroundColor: '#1a1a2e', borderRadius: 6,
                }}>
                  <span style={{ fontSize: 24, opacity: 0.3, display: 'block', marginBottom: 6 }}>📐</span>
                  No schemas defined yet
                </div>
              )}
            </div>

            {performance && (
              <div style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span>🔨</span>Performance Stats
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Total Executions</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#74b9ff' }}>{performance.total_executions.toLocaleString()}</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Success Rate</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#6bcb77' }}>{performance.success_rate}%</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Avg Latency</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>{performance.avg_latency}ms</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>P95 Latency</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#ff9f43' }}>{performance.p95_latency}ms</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>P99 Latency</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#ff6b6b' }}>{performance.p99_latency}ms</div>
                  </div>
                  <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center' }}>
                    <div style={{ fontSize: 9, color: '#666', marginBottom: 2 }}>Active / Deprecated</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#e0e0e0' }}>{performance.active_tools} / {performance.deprecated_tools}</div>
                  </div>
                </div>
              </div>
            )}

            <div>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>🛠️</span>Execution Records
                <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({executions.length})</span>
              </div>
              {executions.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {executions.map(exec => (
                    <div key={exec.id} style={{
                      padding: 8, backgroundColor: '#22223a', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: `3px solid ${EXECUTION_STATUS_COLORS[exec.status]}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 11, fontWeight: 600, color: '#aaa' }}>{exec.tool_name}</span>
                          <span style={{
                            fontSize: 9, padding: '1px 5px', borderRadius: 3,
                            backgroundColor: EXECUTION_STATUS_COLORS[exec.status] + '33',
                            color: EXECUTION_STATUS_COLORS[exec.status], fontWeight: 600,
                            textTransform: 'uppercase',
                          }}>
                            {exec.status}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                          <span style={{ fontSize: 10, color: '#888' }}>{exec.latency_ms}ms</span>
                          <span style={{ fontSize: 10, color: '#666' }}>{formatTime(exec.timestamp)}</span>
                        </div>
                      </div>
                      <div style={{ fontSize: 10, color: '#888' }}>
                        <span style={{ color: '#666' }}>Input:</span> {exec.input_preview}
                      </div>
                      <div style={{ fontSize: 10, color: '#888' }}>
                        <span style={{ color: '#666' }}>Output:</span> {exec.output_preview}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  textAlign: 'center', padding: 24, color: '#555',
                  backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
                }}>
                  <span style={{ fontSize: 32, opacity: 0.3, display: 'block', marginBottom: 8 }}>🔨</span>
                  No execution records yet
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          <span style={{ marginRight: 4 }}>🔨</span>
          {tools.length} tools · {schemas.length} schemas · {activeCount} active
        </span>
        <span>
          {performance ? `${performance.total_executions.toLocaleString()} total executions` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default AgentToolForgePanel;