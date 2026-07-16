import React, { useCallback, useRef, useEffect, useState } from 'react';
import { useEditorStore, type ChatMessage } from '../store/editorStore';
import { agentApi } from '../utils/api';
import { processAIPrompt, detectGameConcept } from '../services/aiService';
import ModelSelector from './ModelSelector';

const QUICK_ACTIONS = [
  { id: 'world', label: 'Generate World', icon: 'fa-globe', prompt: 'Generate a rich game world with terrain, structures, and atmospheric lighting' },
  { id: 'character', label: 'Create Character', icon: 'fa-person', prompt: 'Create a playable character with unique abilities and animations' },
  { id: 'narrative', label: 'Design Story', icon: 'fa-book-open', prompt: 'Design a branching narrative with three story paths and meaningful choices' },
  { id: 'combat', label: 'Balance Combat', icon: 'fa-bolt', prompt: 'Balance the combat system with weapon types, damage scaling, and enemy difficulty' },
  { id: 'npc', label: 'Build NPC', icon: 'fa-robot', prompt: 'Build an intelligent NPC with personality traits, memory, and context-aware dialogue' },
  { id: 'level', label: 'Design Level', icon: 'fa-map', prompt: 'Design a level with challenges, puzzles, rewards, and progression flow' },
];

const SUGGESTIONS = [
  'Design a boss encounter for a fantasy RPG',
  'Create an emergent narrative system',
  'Generate procedural terrain with biomes',
  'Compose adaptive music for exploration',
];

const formatTimestamp = (ts: number): string => {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const renderContent = (content: string): React.ReactNode => {
  const parts = content.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith('```')) {
      const lines = part.replace(/```\w*\n?/, '').replace(/```$/, '').split('\n');
      return (
        <pre key={i} className="bg-[#0a0a0a] border border-[#222] rounded p-2 my-1.5 overflow-x-auto text-[10px] leading-relaxed font-mono text-[#ccc]">
          <code>{lines.join('\n')}</code>
        </pre>
      );
    }
    const segs = part.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
    return (
      <React.Fragment key={i}>
        {segs.map((seg, j) => {
          if (seg.startsWith('**') && seg.endsWith('**')) {
            return <strong key={j} className="font-bold text-white">{seg.slice(2, -2)}</strong>;
          }
          if (seg.startsWith('*') && seg.endsWith('*')) {
            return <em key={j} className="italic text-[#aaa]">{seg.slice(1, -1)}</em>;
          }
          return <React.Fragment key={j}>{seg}</React.Fragment>;
        })}
      </React.Fragment>
    );
  });
};

const MessageBubble: React.FC<{ message: ChatMessage; onPlayGame?: () => void }> = ({ message, onPlayGame }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center my-1.5">
        <span className="text-[9px] text-[#555] bg-[#1a1a1a] px-2 py-0.5 rounded-full">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-3`}>
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold ${
        isUser
          ? 'bg-[#1a1a1a] text-[#888] border border-[#333]'
          : 'bg-gradient-to-br from-orange-500 to-red-600 text-white'
      }`}>
        {isUser ? (
          <i className="fa-solid fa-user text-[10px]" />
        ) : (
          <i className="fa-solid fa-bolt text-[10px]" />
        )}
      </div>
      <div className={`flex-1 min-w-0 max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div className={`text-[10px] text-[#555] mb-0.5 ${isUser ? 'text-right' : 'text-left'}`}>
          {isUser ? 'You' : 'SparkLabs Agent'} · {formatTimestamp(message.timestamp)}
        </div>
        <div className={`rounded-lg px-3 py-2 text-[11px] leading-relaxed break-words ${
          isUser
            ? 'bg-[#1a1a1a] text-[#ddd] border border-[#2a2a2a]'
            : 'bg-[#0f0f0f] text-[#ccc] border border-[#222]'
        }`}>
          {message.isStreaming && !message.content ? (
            <div className="flex items-center gap-1.5 py-0.5">
              <span className="w-1.5 h-1.5 bg-orange-500 rounded-full animate-pulse" />
              <span className="w-1.5 h-1.5 bg-orange-500 rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-orange-500 rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
              <span className="text-[10px] text-[#666] ml-1">Thinking...</span>
            </div>
          ) : (
            <div className="whitespace-pre-wrap">{renderContent(message.content)}</div>
          )}
          {message.isStreaming && message.content && (
            <span className="inline-block w-1.5 h-3 bg-orange-500 ml-0.5 animate-pulse align-middle" />
          )}
        </div>
        {message.actions && message.actions.length > 0 && (
          <div className="flex gap-1 mt-1 flex-wrap">
            {message.actions.map((action, i) => (
              <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-orange-400 border border-orange-900/40">
                <i className="fa-solid fa-check text-[7px] mr-1" />{action}
              </span>
            ))}
          </div>
        )}
        {message.gameGenerated && onPlayGame && (
          <button
            onClick={onPlayGame}
            className="mt-1.5 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-[11px] font-semibold transition-all"
          >
            <i className="fa-solid fa-play text-[9px]" /> Play Game
          </button>
        )}
      </div>
    </div>
  );
};

const AgentChatPanel: React.FC = () => {
  const {
    chatMessages, chatInput, isAgentThinking, chatPanelCollapsed,
    setChatInput, addChatMessage, updateChatMessage, setAgentThinking,
    clearChatMessages, setChatPanelCollapsed, agentId, backendConnected,
    setActiveCenterTab, saveCurrentChatSession, createChatSession,
    setChatHistoryCollapsed,
  } = useEditorStore();

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatMessages]);

  // Switch the editor center area to the viewport tab so the generated
  // game becomes visible in the GameRunner.
  const handlePlayGame = useCallback(() => {
    setActiveCenterTab('viewport');
  }, [setActiveCenterTab]);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isAgentThinking) return;

    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: Date.now(),
    };
    addChatMessage(userMsg);
    setChatInput('');
    setAgentThinking(true);
    setShowSuggestions(false);

    const assistantId = `assistant_${Date.now()}`;
    addChatMessage({
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true,
    });

    try {
      let response: string = '';
      let actions: string[] = [];
      let gameGenerated = false;

      // Always run the local game-generation pipeline — it produces a
      // complete, playable game regardless of backend availability.
      gameGenerated = await processAIPrompt(trimmed);

      if (gameGenerated) {
        const concept = detectGameConcept(trimmed);
        const conceptLabels: Record<string, string> = {
          'boss-battle': 'Boss Battle Arena',
          'narrative': 'Story Narrative Adventure',
          'terrain': 'Procedural Terrain Explorer',
          'music': 'Music Collection Game',
          'platformer': 'Platformer Game',
          'shooter': 'Top-Down Shooter',
          'dungeon': 'Dungeon Crawler RPG',
          'puzzle': 'Puzzle Game',
          'racing': 'Racing Collection Game',
          'exploration': 'Open World Exploration',
        };
        const label = conceptLabels[concept] || 'Game';
        response = `I've generated a **${label}** from your request: "${trimmed}".\n\nThe game is ready in the viewport. Click **Play Game** below to launch it, or switch to the Game view in the viewport toolbar.\n\nThe scene now contains the entities I created — explore the Scene panel to inspect them.`;
      } else if (backendConnected && agentId) {
        const result = await agentApi.think(agentId, trimmed, {
          scene: 'main_world',
          timestamp: Date.now(),
        }) as Record<string, unknown>;
        response = (result?.response || result?.thought || result?.message || JSON.stringify(result, null, 2)) as string;
        if (Array.isArray(result?.actions)) actions = result.actions as string[];
      } else {
        response = `I've processed your request: "${trimmed}".\n\nThe SparkLabs AI Agent system has been notified. Configure an LLM API key in Settings to enable full conversational AI capabilities, or describe a game you want to build and I will generate it.\n\n**What I can help with:**\n- World building and scene composition\n- Character and NPC design with cognitive architecture\n- Narrative design with branching stories\n- Combat balancing and mechanics\n- Procedural content generation\n- Asset synthesis and harmonization\n- Game testing and bug hunting`;
      }

      const chunks = response.match(/.{1,3}/gs) || [response];
      for (let i = 0; i < chunks.length; i++) {
        await new Promise((r) => setTimeout(r, 8));
        updateChatMessage(assistantId, {
          content: chunks.slice(0, i + 1).join(''),
          isStreaming: i < chunks.length - 1,
        });
      }

      updateChatMessage(assistantId, {
        content: response,
        isStreaming: false,
        actions: actions.length > 0 ? actions : undefined,
        gameGenerated,
      });

      // Persist the conversation into the chat history sidebar
      saveCurrentChatSession();
    } catch (err) {
      updateChatMessage(assistantId, {
        content: `I encountered an issue processing that request: ${err instanceof Error ? err.message : 'Unknown error'}. The engine is running in standalone mode — configure an LLM API key in Settings to enable full AI agent capabilities.`,
        isStreaming: false,
      });
    } finally {
      setAgentThinking(false);
    }
  }, [isAgentThinking, addChatMessage, updateChatMessage, setChatInput, setAgentThinking, agentId, backendConnected, saveCurrentChatSession]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(chatInput);
    }
  }, [chatInput, sendMessage]);

  const handleQuickAction = useCallback((prompt: string) => {
    sendMessage(prompt);
  }, [sendMessage]);

  if (chatPanelCollapsed) {
    return (
      <div className="w-10 flex-shrink-0 bg-[#0a0a0a] border-r border-[#1e1e1e] flex flex-col items-center py-3 gap-3">
        <button
          onClick={() => setChatPanelCollapsed(false)}
          className="w-7 h-7 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 text-white flex items-center justify-center hover:opacity-80 transition-opacity"
          title="Expand AI Agent Chat"
        >
          <i className="fa-solid fa-bolt text-[11px]" />
        </button>
      </div>
    );
  }

  const hasMessages = chatMessages.length > 1;

  return (
    <div className="h-full flex flex-col bg-[#0a0a0a] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1e1e1e] bg-[#0d0d0d]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center">
            <i className="fa-solid fa-bolt text-[10px] text-white" />
          </div>
          <div>
            <div className="text-[11px] font-semibold text-[#ddd]">AI Agent</div>
            <div className="text-[8px] text-[#555]">AI-Native Game Development</div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => createChatSession()}
            className="w-6 h-6 rounded hover:bg-[#1a1a1a] text-[#555] hover:text-orange-400 flex items-center justify-center transition-colors"
            title="New chat"
          >
            <i className="fa-solid fa-pen-to-square text-[9px]" />
          </button>
          <button
            onClick={clearChatMessages}
            className="w-6 h-6 rounded hover:bg-[#1a1a1a] text-[#555] hover:text-[#888] flex items-center justify-center transition-colors"
            title="Clear chat"
          >
            <i className="fa-solid fa-trash-can text-[9px]" />
          </button>
          <button
            onClick={() => setChatPanelCollapsed(true)}
            className="w-6 h-6 rounded hover:bg-[#1a1a1a] text-[#555] hover:text-[#888] flex items-center justify-center transition-colors"
            title="Collapse panel"
          >
            <i className="fa-solid fa-angles-left text-[9px]" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 sl-chat-scroll">
        {chatMessages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onPlayGame={handlePlayGame} />
        ))}

        {!hasMessages && !isAgentThinking && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center mb-3">
              <i className="fa-solid fa-bolt text-white text-lg" />
            </div>
            <div className="text-[12px] font-semibold text-[#aaa] mb-1">AI-Native Game Engine</div>
            <div className="text-[10px] text-[#555] mb-4 leading-relaxed">
              Chat with your AI Agent to design worlds, create characters, direct narratives, and build games through natural conversation.
            </div>
            <div className="w-full space-y-1.5">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(s)}
                  className="w-full text-left text-[10px] text-[#777] px-3 py-2 rounded-lg bg-[#111] border border-[#1e1e1e] hover:border-orange-900/40 hover:text-orange-400 transition-all"
                >
                  <i className="fa-solid fa-lightbulb text-[8px] mr-2 text-[#444]" />
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {hasMessages && !isAgentThinking && (
          <div className="mt-2 mb-1">
            <button
              onClick={() => setShowSuggestions(!showSuggestions)}
              className="text-[9px] text-[#444] hover:text-[#666] flex items-center gap-1"
            >
              <i className={`fa-solid fa-chevron-${showSuggestions ? 'up' : 'down'} text-[7px]`} />
              Quick Actions
            </button>
            {showSuggestions && (
              <div className="grid grid-cols-2 gap-1 mt-1.5">
                {QUICK_ACTIONS.map((action) => (
                  <button
                    key={action.id}
                    onClick={() => handleQuickAction(action.prompt)}
                    className="text-left text-[9px] text-[#777] px-2 py-1.5 rounded bg-[#0f0f0f] border border-[#1e1e1e] hover:border-orange-900/40 hover:text-orange-400 transition-all flex items-center gap-1.5"
                  >
                    <i className={`fa-solid ${action.icon} text-[8px] text-[#444]`} />
                    {action.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-[#1e1e1e] p-2.5 bg-[#0d0d0d]">
        {/* Model selector — choose AI model before interaction */}
        <div className="mb-2">
          <ModelSelector />
        </div>
        <div className="relative">
          <textarea
            ref={inputRef}
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your game vision..."
            rows={2}
            disabled={isAgentThinking}
            className="w-full bg-[#0a0a0a] border border-[#1e1e1e] rounded-lg px-3 py-2 pr-10 text-[11px] text-[#ccc] placeholder-[#444] resize-none focus:outline-none focus:border-orange-900/50 disabled:opacity-50 sl-chat-input"
          />
          <button
            onClick={() => sendMessage(chatInput)}
            disabled={!chatInput.trim() || isAgentThinking}
            className="absolute right-2 bottom-2 w-7 h-7 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 text-white flex items-center justify-center disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-80 transition-opacity"
            title="Send message"
          >
            <i className="fa-solid fa-paper-plane text-[10px]" />
          </button>
        </div>
        <div className="flex items-center justify-between mt-1.5 px-1">
          <div className="flex items-center gap-2 text-[8px] text-[#444]">
            <span>Shift+Enter for newline</span>
          </div>
          <span className="text-[8px] text-[#333] font-mono">{chatInput.length} chars</span>
        </div>
      </div>
    </div>
  );
};

export default AgentChatPanel;
