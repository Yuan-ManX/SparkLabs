"use client";

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Send, Brain, Zap, Cpu, ChevronDown, Loader2,
  Image, Video, Music, Box, Mic, Activity, Server,
  CheckCircle, AlertCircle, RefreshCw,
} from 'lucide-react';
import { agentChatApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatResponse {
  response: string;
  content_urls?: string[];
  task_type: string;
  provider_id: string;
  model_id: string;
  simulated: boolean;
  cached: boolean;
  fallback_used: boolean;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  cost: number;
  finish_reason: string;
}

interface ChatHistoryEntry {
  id: string;
  session_id: string;
  timestamp: number;
  user_message: string;
  agent_response: string;
  task_type: string;
  provider_id: string;
  model_id: string;
  simulated: boolean;
  cached: boolean;
  fallback_used: boolean;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  cost: number;
}

interface TaskType {
  value: string;
  name: string;
  description: string;
}

interface ModelEntry {
  model_id: string;
  provider_id: string;
  model_type: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  routing?: {
    task_type: string;
    provider_id: string;
    model_id: string;
    simulated: boolean;
    cached: boolean;
    latency_ms: number;
    tokens: number;
  };
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const panelStyle: React.CSSProperties = {
  background: '#0a0a0a',
  color: '#e2e8f0',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  fontSize: '12px',
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
};

const cardStyle: React.CSSProperties = {
  background: '#111',
  border: '1px solid #222',
  borderRadius: '8px',
  padding: '12px',
};

const buttonBase: React.CSSProperties = {
  padding: '6px 12px',
  borderRadius: '6px',
  fontSize: '11px',
  fontWeight: 600,
  cursor: 'pointer',
  border: '1px solid #333',
  background: '#1a1a1a',
  color: '#e2e8f0',
  transition: 'all 0.15s',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '4px',
};

const taskTypeColor = (task: string): string => {
  const colors: Record<string, string> = {
    world_building: '#22c55e',
    character_design: '#3b82f6',
    dialogue: '#a855f7',
    code_gen: '#f97316',
    asset_image: '#ec4899',
    asset_video: '#06b6d4',
    asset_3d: '#eab308',
    asset_audio: '#f43f5e',
    music_gen: '#8b5cf6',
    voice_acting: '#14b8a6',
    bug_analysis: '#ef4444',
    balance_test: '#fbbf24',
    narrative: '#a855f7',
    translation: '#6366f1',
    summarization: '#64748b',
  };
  return colors[task] || '#666';
};

// ---------------------------------------------------------------------------
// Quick Action Buttons
// ---------------------------------------------------------------------------

const QUICK_ACTIONS = [
  { label: 'Generate World', prompt: 'Generate a rich game world with terrain, mountains, rivers, and atmospheric lighting', icon: '🌍' },
  { label: 'Create Character', prompt: 'Create a playable character with unique abilities, stats, and animation states', icon: '🦸' },
  { label: 'Design Story', prompt: 'Design a branching narrative with three story paths and meaningful player choices', icon: '📖' },
  { label: 'Write Code', prompt: 'Write a Python function to implement a procedural dungeon generator using BSP', icon: '💻' },
  { label: 'Balance Combat', prompt: 'Balance the combat system with weapon types, damage scaling, and enemy difficulty curves', icon: '⚔️' },
  { label: 'Design Level', prompt: 'Design a level with challenges, puzzles, rewards, and a natural progression flow', icon: '🗺️' },
];

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const ModelChatPanel: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [taskTypes, setTaskTypes] = useState<TaskType[]>([]);
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [selectedTaskType, setSelectedTaskType] = useState<string>('');
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [simulationMode, setSimulationMode] = useState(true);
  const [status, setStatus] = useState<{ provider_count: number; model_count: number; simulation_mode: boolean } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load initial data
  const loadInitialData = useCallback(async () => {
    try {
      const [taskRes, modelsRes, statusRes] = await Promise.all([
        agentChatApi.getTaskTypes(),
        agentChatApi.getModels(),
        agentChatApi.getStatus(),
      ]);
      const td = (taskRes.data as any)?.data || {};
      setTaskTypes(td.task_types || []);

      const md = (modelsRes.data as any)?.data || {};
      setModels(md.all_models || []);

      const sd = (statusRes.data as any)?.data || {};
      setStatus({
        provider_count: sd.provider_count || 0,
        model_count: sd.model_count || 0,
        simulation_mode: sd.simulation_mode ?? true,
      });
      setSimulationMode(sd.simulation_mode ?? true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Send message
  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);
    setError(null);

    // Add user message
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, timestamp: Date.now() },
    ]);

    try {
      const res = await agentChatApi.sendMessage({
        message: userMessage,
        session_id: 'model-chat',
        model_id: selectedModel || undefined,
        provider_id: selectedProvider || undefined,
        task_type: selectedTaskType || undefined,
      });

      const data = (res.data as any)?.data || res.data;
      const response: ChatResponse = data;

      // Add assistant message with routing metadata
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.response || '(No response)',
          timestamp: Date.now(),
          routing: {
            task_type: response.task_type,
            provider_id: response.provider_id,
            model_id: response.model_id,
            simulated: response.simulated,
            cached: response.cached,
            latency_ms: response.latency_ms,
            tokens: (response.input_tokens || 0) + (response.output_tokens || 0),
          },
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Handle quick action
  const handleQuickAction = (prompt: string) => {
    setInput(prompt);
  };

  // Toggle simulation mode
  const handleToggleSimulation = async () => {
    try {
      await agentChatApi.setSimulation(!simulationMode);
      setSimulationMode(!simulationMode);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Toggle failed');
    }
  };

  // Clear chat
  const handleClear = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #222', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Brain size={18} color="#a855f7" />
          <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>Model Chat</span>
          {status && (
            <span style={{ fontSize: '10px', color: '#666' }}>
              {status.provider_count} providers · {status.model_count} models
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            style={{
              ...buttonBase,
              background: simulationMode ? '#fbbf24' : '#22c55e',
              color: '#000',
              borderColor: simulationMode ? '#fbbf24' : '#22c55e',
            }}
            onClick={handleToggleSimulation}
            title="Toggle simulation mode"
          >
            {simulationMode ? 'SIM' : 'LIVE'}
          </button>
          <button style={buttonBase} onClick={loadInitialData} title="Refresh">
            <RefreshCw size={12} />
          </button>
          <button style={buttonBase} onClick={handleClear} title="Clear chat">
            Clear
          </button>
        </div>
      </div>

      {/* Model Selector Bar */}
      <div style={{ padding: '8px 16px', borderBottom: '1px solid #1a1a1a', display: 'flex', gap: '8px', alignItems: 'center' }}>
        <button
          style={{
            ...buttonBase,
            borderColor: showModelSelector ? '#a855f7' : '#333',
            background: showModelSelector ? '#a855f715' : '#1a1a1a',
          }}
          onClick={() => setShowModelSelector(!showModelSelector)}
        >
          <Cpu size={12} />
          {selectedModel ? selectedModel : 'Auto-Route'}
          <ChevronDown size={10} />
        </button>
        {selectedTaskType && (
          <span style={{
            fontSize: '9px',
            padding: '2px 6px',
            borderRadius: '4px',
            background: taskTypeColor(selectedTaskType) + '22',
            color: taskTypeColor(selectedTaskType),
          }}>
            {selectedTaskType}
          </span>
        )}
        {(selectedModel || selectedTaskType) && (
          <button
            style={{ ...buttonBase, padding: '3px 8px', fontSize: '9px' }}
            onClick={() => {
              setSelectedModel('');
              setSelectedProvider('');
              setSelectedTaskType('');
            }}
          >
            Reset
          </button>
        )}
      </div>

      {/* Model Selector Dropdown */}
      {showModelSelector && (
        <div style={{ padding: '8px 16px', borderBottom: '1px solid #1a1a1a', maxHeight: '200px', overflowY: 'auto' }}>
          <div style={{ marginBottom: '8px' }}>
            <div style={{ fontSize: '10px', color: '#666', marginBottom: '4px' }}>Task Type (optional)</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              <button
                style={{
                  ...buttonBase,
                  padding: '3px 8px',
                  fontSize: '9px',
                  borderColor: !selectedTaskType ? '#a855f7' : '#333',
                  background: !selectedTaskType ? '#a855f715' : '#1a1a1a',
                }}
                onClick={() => setSelectedTaskType('')}
              >
                Auto
              </button>
              {taskTypes.map((tt) => (
                <button
                  key={tt.value}
                  style={{
                    ...buttonBase,
                    padding: '3px 8px',
                    fontSize: '9px',
                    borderColor: selectedTaskType === tt.value ? taskTypeColor(tt.value) : '#333',
                    background: selectedTaskType === tt.value ? taskTypeColor(tt.value) + '15' : '#1a1a1a',
                    color: selectedTaskType === tt.value ? taskTypeColor(tt.value) : '#ccc',
                  }}
                  onClick={() => setSelectedTaskType(tt.value)}
                  title={tt.description}
                >
                  {tt.value}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '10px', color: '#666', marginBottom: '4px' }}>Model (optional)</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              <button
                style={{
                  ...buttonBase,
                  padding: '3px 8px',
                  fontSize: '9px',
                  borderColor: !selectedModel ? '#a855f7' : '#333',
                  background: !selectedModel ? '#a855f715' : '#1a1a1a',
                }}
                onClick={() => {
                  setSelectedModel('');
                  setSelectedProvider('');
                }}
              >
                Auto-Route
              </button>
              {models.slice(0, 30).map((m) => (
                <button
                  key={m.model_id}
                  style={{
                    ...buttonBase,
                    padding: '3px 8px',
                    fontSize: '9px',
                    borderColor: selectedModel === m.model_id ? '#a855f7' : '#333',
                    background: selectedModel === m.model_id ? '#a855f715' : '#1a1a1a',
                  }}
                  onClick={() => {
                    setSelectedModel(m.model_id);
                    setSelectedProvider(m.provider_id);
                  }}
                >
                  {m.model_id}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: '#555' }}>
            <Brain size={32} color="#333" style={{ margin: '0 auto 12px' }} />
            <div style={{ fontSize: '13px', marginBottom: '4px' }}>Chat with the AI agent</div>
            <div style={{ fontSize: '11px', color: '#444' }}>
              Messages are routed to the optimal model based on task type.
              {simulationMode && ' (Simulation mode - no API keys needed)'}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                gap: '8px',
                marginBottom: '16px',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              }}
            >
              {/* Avatar */}
              <div
                style={{
                  flexShrink: 0,
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '11px',
                  fontWeight: 700,
                  background: msg.role === 'user' ? '#1a1a1a' : 'linear-gradient(135deg, #a855f7, #6366f1)',
                  color: msg.role === 'user' ? '#888' : '#fff',
                  border: msg.role === 'user' ? '1px solid #333' : 'none',
                }}
              >
                {msg.role === 'user' ? 'U' : <Zap size={12} />}
              </div>

              {/* Message Content */}
              <div style={{ flex: 1, maxWidth: '80%' }}>
                <div style={{ fontSize: '9px', color: '#555', marginBottom: '2px' }}>
                  {msg.role === 'user' ? 'You' : 'Agent'} · {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
                <div
                  style={{
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontSize: '12px',
                    lineHeight: 1.5,
                    whiteSpace: 'pre-wrap',
                    background: msg.role === 'user' ? '#1a1a1a' : '#0f0f0f',
                    border: msg.role === 'user' ? '1px solid #2a2a2a' : '1px solid #222',
                    color: '#ccc',
                  }}
                >
                  {msg.content}
                </div>

                {/* Routing Metadata */}
                {msg.routing && (
                  <div style={{ display: 'flex', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
                    <span style={{
                      fontSize: '9px',
                      padding: '1px 6px',
                      borderRadius: '3px',
                      background: taskTypeColor(msg.routing.task_type) + '22',
                      color: taskTypeColor(msg.routing.task_type),
                    }}>
                      {msg.routing.task_type}
                    </span>
                    <span style={{
                      fontSize: '9px',
                      padding: '1px 6px',
                      borderRadius: '3px',
                      background: '#222',
                      color: '#888',
                    }}>
                      {msg.routing.provider_id}/{msg.routing.model_id}
                    </span>
                    {msg.routing.simulated && (
                      <span style={{
                        fontSize: '9px',
                        padding: '1px 6px',
                        borderRadius: '3px',
                        background: '#fbbf2415',
                        color: '#fbbf24',
                      }}>
                        SIMULATED
                      </span>
                    )}
                    {msg.routing.cached && (
                      <span style={{
                        fontSize: '9px',
                        padding: '1px 6px',
                        borderRadius: '3px',
                        background: '#22c55e15',
                        color: '#22c55e',
                      }}>
                        CACHED
                      </span>
                    )}
                    <span style={{
                      fontSize: '9px',
                      padding: '1px 6px',
                      borderRadius: '3px',
                      background: '#222',
                      color: '#666',
                    }}>
                      {msg.routing.latency_ms.toFixed(0)}ms
                    </span>
                    {msg.routing.tokens > 0 && (
                      <span style={{
                        fontSize: '9px',
                        padding: '1px 6px',
                        borderRadius: '3px',
                        background: '#222',
                        color: '#666',
                      }}>
                        {msg.routing.tokens} tok
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
            <div style={{
              flexShrink: 0,
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'linear-gradient(135deg, #a855f7, #6366f1)',
            }}>
              <Loader2 size={12} color="#fff" className="animate-spin" />
            </div>
            <div style={{
              borderRadius: '8px',
              padding: '8px 12px',
              background: '#0f0f0f',
              border: '1px solid #222',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}>
              <span style={{ fontSize: '11px', color: '#666' }}>Routing to optimal model...</span>
            </div>
          </div>
        )}

        {error && (
          <div style={{
            fontSize: '10px',
            color: '#ef4444',
            background: '#ef444415',
            border: '1px solid #ef444433',
            borderRadius: '6px',
            padding: '6px 10px',
            marginBottom: '8px',
          }}>
            <AlertCircle size={10} style={{ display: 'inline', marginRight: '4px' }} />
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      {messages.length === 0 && (
        <div style={{ padding: '0 16px 8px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              style={{
                ...buttonBase,
                fontSize: '10px',
                padding: '4px 10px',
              }}
              onClick={() => handleQuickAction(action.prompt)}
            >
              {action.icon} {action.label}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid #222', display: 'flex', gap: '8px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Type a message... (Enter to send)"
          disabled={loading}
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: '6px',
            background: '#111',
            border: '1px solid #333',
            color: '#e2e8f0',
            fontSize: '12px',
            fontFamily: 'inherit',
            outline: 'none',
          }}
        />
        <button
          style={{
            ...buttonBase,
            background: '#a855f7',
            color: '#fff',
            borderColor: '#a855f7',
            opacity: loading || !input.trim() ? 0.5 : 1,
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
          }}
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          <Send size={12} />
          Send
        </button>
      </div>
    </div>
  );
};

export default ModelChatPanel;
