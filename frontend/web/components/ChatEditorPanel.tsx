"use client";

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Send, Brain, Zap, Cpu, Loader2, Code, Box, Image,
  Bug, Scale, List, Info, Gamepad2, CheckCircle, XCircle,
  RefreshCw, Trash2, ChevronDown,
} from 'lucide-react';
import { chatEditorApi, agentChatApi } from '../utils/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface EditorActionResult {
  action_type: string;
  message: string;
  success: boolean;
  result: Record<string, unknown>;
  error: string | null;
  elapsed_ms: number;
  timestamp: number;
  session_id: string;
  provider_id?: string;
  model_id?: string;
  simulated?: boolean;
}

interface ChatMessage {
  role: 'user' | 'assistant' | 'editor';
  content: string;
  timestamp: number;
  actionType?: string;
  routing?: {
    provider: string;
    model: string;
    simulated: boolean;
    latency_ms: number;
  };
  editorResult?: {
    success: boolean;
    actionType: string;
    result: Record<string, unknown>;
    elapsed_ms: number;
  };
}

interface EditorAction {
  action: string;
  description: string;
  examples: string[];
}

// ---------------------------------------------------------------------------
// Action icons and colors
// ---------------------------------------------------------------------------

const ACTION_ICONS: Record<string, React.ReactNode> = {
  create_game: <Gamepad2 size={14} />,
  create_entity: <Box size={14} />,
  create_scene: <Image size={14} />,
  generate_code: <Code size={14} />,
  generate_asset: <Image size={14} />,
  analyze_bug: <Bug size={14} />,
  balance_game: <Scale size={14} />,
  list_scene: <List size={14} />,
  editor_status: <Info size={14} />,
  create_dialogue: <Brain size={14} />,
  generate_level: <Gamepad2 size={14} />,
  create_animation: <Zap size={14} />,
};

const ACTION_COLORS: Record<string, string> = {
  create_game: '#22c55e',
  create_entity: '#3b82f6',
  create_scene: '#06b6d4',
  generate_code: '#f97316',
  generate_asset: '#ec4899',
  analyze_bug: '#ef4444',
  balance_game: '#fbbf24',
  list_scene: '#6366f1',
  editor_status: '#64748b',
  create_dialogue: '#a855f7',
  generate_level: '#14b8a6',
  create_animation: '#f59e0b',
};

// ---------------------------------------------------------------------------
// Quick Actions
// ---------------------------------------------------------------------------

const QUICK_ACTIONS = [
  { label: 'Create Game', prompt: 'Create a platformer game with double jump and coin collection', icon: <Gamepad2 size={12} /> },
  { label: 'Create Entity', prompt: 'Create a player character with sword and shield', icon: <Box size={12} /> },
  { label: 'Generate Code', prompt: 'Write a Python function to implement a procedural dungeon generator', icon: <Code size={12} /> },
  { label: 'Generate Image', prompt: 'Generate an image of a fantasy castle on a mountain', icon: <Image size={12} /> },
  { label: 'Analyze Bug', prompt: 'The player falls through the floor when jumping on moving platforms', icon: <Bug size={12} /> },
  { label: 'Balance Game', prompt: 'The game difficulty is too hard, balance the combat system', icon: <Scale size={12} /> },
  { label: 'Create Dialogue', prompt: 'Create NPC dialogue for a shopkeeper who sells potions', icon: <Brain size={12} /> },
  { label: 'Generate Level', prompt: 'Generate a dungeon level with traps and treasure rooms', icon: <Gamepad2 size={12} /> },
  { label: 'Create Animation', prompt: 'Create a walk cycle animation for the player character', icon: <Zap size={12} /> },
];

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

// ---------------------------------------------------------------------------
// Main Panel
// ---------------------------------------------------------------------------

const ChatEditorPanel: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actions, setActions] = useState<EditorAction[]>([]);
  const [showActions, setShowActions] = useState(false);
  const [mode, setMode] = useState<'editor' | 'chat'>('editor');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load available actions
  const loadActions = useCallback(async () => {
    try {
      const res = await chatEditorApi.getActions();
      const data = (res as any)?.data?.data || (res as any)?.data || {};
      setActions(data.actions || []);
    } catch (err) {
      // Silent fail
    }
  }, []);

  useEffect(() => {
    loadActions();
  }, [loadActions]);

  // Auto-scroll
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

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: userMessage, timestamp: Date.now() },
    ]);

    try {
      if (mode === 'editor') {
        // Execute through chat-editor bridge
        const res = await chatEditorApi.execute({
          message: userMessage,
          session_id: 'chat-editor',
        });
        const data = (res as any)?.data?.data || (res as any)?.data || {};
        const result: EditorActionResult = data;

        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: _formatEditorResult(result),
            timestamp: Date.now(),
            actionType: result.action_type,
            routing: result.provider_id ? {
              provider: result.provider_id,
              model: result.model_id || '',
              simulated: result.simulated || false,
              latency_ms: result.elapsed_ms,
            } : undefined,
            editorResult: {
              success: result.success,
              actionType: result.action_type,
              result: result.result || {},
              elapsed_ms: result.elapsed_ms,
            },
          },
        ]);
      } else {
        // Chat only mode - use agent chat API
        const res = await agentChatApi.sendMessage({
          message: userMessage,
          session_id: 'chat-only',
        });
        const data = (res as any)?.data?.data || (res as any)?.data || {};

        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.response || '(No response)',
            timestamp: Date.now(),
            actionType: data.task_type,
            routing: {
              provider: data.provider_id || '',
              model: data.model_id || '',
              simulated: data.simulated || false,
              latency_ms: data.latency_ms || 0,
            },
          },
        ]);
      }
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errMsg);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${errMsg}`, timestamp: Date.now() },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Format editor result as readable text
  const _formatEditorResult = (result: EditorActionResult): string => {
    if (!result.success) {
      return `Action failed: ${result.error || 'Unknown error'}`;
    }
    const r = result.result || {};
    switch (result.action_type) {
      case 'generate_code':
        return (r.code as string) || '(No code generated)';
      case 'analyze_bug':
        return (r.analysis as string) || '(No analysis)';
      case 'balance_game':
        return (r.suggestions as string) || '(No suggestions)';
      case 'create_entity':
        return `Entity created: ${r.entity_id} (type: ${r.type})\nDescription: ${r.name}`;
      case 'create_scene':
        return `Scene created: ${r.scene_id}\nName: ${r.name}`;
      case 'generate_asset':
        return `Asset generated: ${r.modality}\nURLs: ${JSON.stringify(r.content_urls)}`;
      case 'editor_status':
        return `Mode: ${r.mode}\nActive scene: ${r.active_scene}\nAvailable actions: ${JSON.stringify(r.available_actions)}`;
      case 'list_scene':
        return `Scene: ${r.scene_id}\nEntities: ${r.entity_count}`;
      case 'create_game':
        return `Game created: ${r.run_id || 'success'}`;
      case 'create_dialogue':
        return (r.dialogue as string) || '(No dialogue generated)';
      case 'generate_level':
        return (r.level_data as string) || '(No level data generated)';
      case 'create_animation':
        return `Animation type: ${r.animation_type}\n${(r.animation_data as string) || '(No animation data)'}`;
      default:
        return JSON.stringify(r, null, 2);
    }
  };

  // Clear messages
  const handleClear = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div style={panelStyle}>
      {/* Header */}
      <div style={{ padding: '10px 14px', borderBottom: '1px solid #222', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Brain size={16} color="#a855f7" />
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>Chat Editor</span>
          <div style={{ display: 'flex', gap: '4px', marginLeft: '8px' }}>
            <button
              style={{
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '9px',
                fontWeight: 600,
                border: '1px solid',
                borderColor: mode === 'editor' ? '#f97316' : '#333',
                background: mode === 'editor' ? '#f9731615' : '#111',
                color: mode === 'editor' ? '#f97316' : '#666',
                cursor: 'pointer',
              }}
              onClick={() => setMode('editor')}
            >
              EDITOR
            </button>
            <button
              style={{
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '9px',
                fontWeight: 600,
                border: '1px solid',
                borderColor: mode === 'chat' ? '#a855f7' : '#333',
                background: mode === 'chat' ? '#a855f715' : '#111',
                color: mode === 'chat' ? '#a855f7' : '#666',
                cursor: 'pointer',
              }}
              onClick={() => setMode('chat')}
            >
              CHAT
            </button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            style={{
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '10px',
              border: '1px solid #333',
              background: '#111',
              color: '#888',
              cursor: 'pointer',
            }}
            onClick={() => setShowActions(!showActions)}
            title="Show available actions"
          >
            <List size={10} />
          </button>
          <button
            style={{
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '10px',
              border: '1px solid #333',
              background: '#111',
              color: '#888',
              cursor: 'pointer',
            }}
            onClick={handleClear}
            title="Clear"
          >
            <Trash2 size={10} />
          </button>
        </div>
      </div>

      {/* Available Actions Panel */}
      {showActions && (
        <div style={{ padding: '8px 14px', borderBottom: '1px solid #1a1a1a', maxHeight: '180px', overflowY: 'auto' }}>
          <div style={{ fontSize: '10px', color: '#666', marginBottom: '6px' }}>Available Editor Actions:</div>
          {actions.map((a) => (
            <div key={a.action} style={{ marginBottom: '4px', padding: '4px 6px', borderRadius: '4px', background: '#0a0a0a', border: '1px solid #1a1a1a' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: ACTION_COLORS[a.action] || '#666' }}>
                  {ACTION_ICONS[a.action] || <Info size={12} />}
                </span>
                <span style={{ fontSize: '11px', fontWeight: 600, color: '#ccc' }}>{a.action}</span>
              </div>
              <div style={{ fontSize: '9px', color: '#555', marginLeft: '20px' }}>{a.description}</div>
            </div>
          ))}
        </div>
      )}

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 14px' }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: '#555' }}>
            <Brain size={32} color="#333" style={{ margin: '0 auto 10px' }} />
            <div style={{ fontSize: '12px', marginBottom: '4px' }}>
              {mode === 'editor' ? 'Chat to control the editor' : 'Chat with AI models'}
            </div>
            <div style={{ fontSize: '10px', color: '#444' }}>
              {mode === 'editor'
                ? 'Type a message and the agent will classify it, route to the best model, and execute the editor action.'
                : 'Messages are routed to the optimal model based on task type.'}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} style={{ display: 'flex', gap: '8px', marginBottom: '14px', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
              {/* Avatar */}
              <div style={{
                flexShrink: 0,
                width: '26px',
                height: '26px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: msg.role === 'user' ? '#1a1a1a' : 'linear-gradient(135deg, #a855f7, #6366f1)',
                color: msg.role === 'user' ? '#888' : '#fff',
                border: msg.role === 'user' ? '1px solid #333' : 'none',
              }}>
                {msg.role === 'user' ? 'U' : <Zap size={12} />}
              </div>

              {/* Content */}
              <div style={{ flex: 1, maxWidth: '82%' }}>
                <div style={{ fontSize: '9px', color: '#555', marginBottom: '2px' }}>
                  {msg.role === 'user' ? 'You' : 'Agent'} · {new Date(msg.timestamp).toLocaleTimeString()}
                </div>

                {/* Action type badge */}
                {msg.actionType && (
                  <div style={{ marginBottom: '3px' }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '9px',
                      padding: '2px 6px',
                      borderRadius: '3px',
                      background: (ACTION_COLORS[msg.actionType] || '#666') + '22',
                      color: ACTION_COLORS[msg.actionType] || '#666',
                    }}>
                      {ACTION_ICONS[msg.actionType] || <Info size={10} />}
                      {msg.actionType}
                    </span>
                  </div>
                )}

                {/* Message body */}
                <div style={{
                  borderRadius: '8px',
                  padding: '8px 12px',
                  fontSize: '11px',
                  lineHeight: 1.5,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  background: msg.role === 'user' ? '#1a1a1a' : '#0f0f0f',
                  border: msg.role === 'user' ? '1px solid #2a2a2a' : '1px solid #222',
                  color: '#ccc',
                  maxHeight: '300px',
                  overflowY: 'auto',
                }}>
                  {msg.content}
                </div>

                {/* Routing + Editor Result metadata */}
                <div style={{ display: 'flex', gap: '4px', marginTop: '3px', flexWrap: 'wrap' }}>
                  {msg.routing && (
                    <>
                      <span style={{ fontSize: '8px', padding: '1px 5px', borderRadius: '3px', background: '#222', color: '#888' }}>
                        {msg.routing.provider}/{msg.routing.model}
                      </span>
                      {msg.routing.simulated && (
                        <span style={{ fontSize: '8px', padding: '1px 5px', borderRadius: '3px', background: '#fbbf2415', color: '#fbbf24' }}>
                          SIM
                        </span>
                      )}
                      <span style={{ fontSize: '8px', padding: '1px 5px', borderRadius: '3px', background: '#222', color: '#666' }}>
                        {msg.routing.latency_ms?.toFixed(0)}ms
                      </span>
                    </>
                  )}
                  {msg.editorResult && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '2px',
                      fontSize: '8px',
                      padding: '1px 5px',
                      borderRadius: '3px',
                      background: msg.editorResult.success ? '#22c55e15' : '#ef444415',
                      color: msg.editorResult.success ? '#22c55e' : '#ef4444',
                    }}>
                      {msg.editorResult.success ? <CheckCircle size={8} /> : <XCircle size={8} />}
                        {msg.editorResult.success ? 'EXECUTED' : 'FAILED'} · {msg.editorResult.elapsed_ms?.toFixed(0)}ms
                      </span>
                    )}
                </div>
              </div>
            </div>
          ))
        )}

        {loading && (
          <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
            <div style={{
              flexShrink: 0,
              width: '26px',
              height: '26px',
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
            }}>
              <span style={{ fontSize: '10px', color: '#666' }}>
                {mode === 'editor' ? 'Classifying action, routing to model, executing...' : 'Routing to optimal model...'}
              </span>
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
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      {messages.length === 0 && (
        <div style={{ padding: '0 14px 6px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              style={{
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '9px',
                fontWeight: 600,
                border: '1px solid #333',
                background: '#111',
                color: '#aaa',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
              onClick={() => setInput(action.prompt)}
            >
              {action.icon}
              {action.label}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{ padding: '10px 14px', borderTop: '1px solid #222', display: 'flex', gap: '6px' }}>
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
          placeholder={mode === 'editor' ? 'Type to control the editor...' : 'Type a message...'}
          disabled={loading}
          style={{
            flex: 1,
            padding: '7px 10px',
            borderRadius: '6px',
            background: '#111',
            border: '1px solid #333',
            color: '#e2e8f0',
            fontSize: '11px',
            fontFamily: 'inherit',
            outline: 'none',
          }}
        />
        <button
          style={{
            padding: '7px 14px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 600,
            border: 'none',
            background: mode === 'editor' ? '#f97316' : '#a855f7',
            color: '#fff',
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            opacity: loading || !input.trim() ? 0.5 : 1,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          <Send size={11} />
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatEditorPanel;
