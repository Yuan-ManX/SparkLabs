import React, { useState, useMemo } from 'react';
import { useEditorStore, type ChatSession } from '../store/editorStore';

// Group sessions by relative date for display.
function getDateGroup(timestamp: number): string {
  const now = new Date();
  const date = new Date(timestamp);
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterdayStart = todayStart - 86400000;
  const weekStart = todayStart - 6 * 86400000;

  if (timestamp >= todayStart) return 'Today';
  if (timestamp >= yesterdayStart) return 'Yesterday';
  if (timestamp >= weekStart) return 'Previous 7 Days';
  return 'Older';
}

const GROUP_ORDER = ['Today', 'Yesterday', 'Previous 7 Days', 'Older'];

const formatTime = (ts: number): string => {
  const d = new Date(ts);
  const now = new Date();
  const diff = now.getTime() - ts;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
};

const ChatHistorySidebar: React.FC = () => {
  const {
    chatHistoryCollapsed,
    chatSessions,
    activeChatSessionId,
    setChatHistoryCollapsed,
    createChatSession,
    loadChatSession,
    deleteChatSession,
  } = useEditorStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Filter and group sessions by date
  const groupedSessions = useMemo(() => {
    const filtered = searchQuery.trim()
      ? chatSessions.filter((s) =>
          s.title.toLowerCase().includes(searchQuery.toLowerCase().trim())
        )
      : chatSessions;

    const groups: Record<string, ChatSession[]> = {};
    for (const session of filtered) {
      const group = getDateGroup(session.updatedAt);
      if (!groups[group]) groups[group] = [];
      groups[group].push(session);
    }
    // Sort each group by updatedAt descending
    for (const key of Object.keys(groups)) {
      groups[key].sort((a, b) => b.updatedAt - a.updatedAt);
    }
    return groups;
  }, [chatSessions, searchQuery]);

  // Collapsed state: narrow strip with toggle button
  if (chatHistoryCollapsed) {
    return (
      <div className="w-10 flex-shrink-0 bg-[#0a0a0a] border-r border-[#1a1a1a] flex flex-col items-center py-2 gap-2">
        <button
          onClick={() => setChatHistoryCollapsed(false)}
          className="w-7 h-7 rounded-lg bg-[#1a1a1a] hover:bg-[#222] text-[#888] hover:text-[#ccc] flex items-center justify-center transition-colors"
          title="Open chat history"
        >
          <i className="fa-solid fa-bars-staggered text-[11px]" />
        </button>
        <button
          onClick={() => {
            createChatSession();
            setChatHistoryCollapsed(false);
          }}
          className="w-7 h-7 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 text-white flex items-center justify-center hover:opacity-80 transition-opacity"
          title="New chat"
        >
          <i className="fa-solid fa-pen-to-square text-[10px]" />
        </button>
      </div>
    );
  }

  // Expanded state: full sidebar
  return (
    <div className="w-[260px] flex-shrink-0 bg-[#0a0a0a] border-r border-[#1a1a1a] flex flex-col overflow-hidden">
      {/* Header with toggle and new chat */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-[#1a1a1a]">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setChatHistoryCollapsed(true)}
            className="w-7 h-7 rounded-lg bg-[#1a1a1a] hover:bg-[#222] text-[#888] hover:text-[#ccc] flex items-center justify-center transition-colors"
            title="Collapse history"
          >
            <i className="fa-solid fa-bars-staggered text-[11px]" />
          </button>
          <span className="text-[11px] font-semibold text-[#aaa]">Chat History</span>
        </div>
        <button
          onClick={() => createChatSession()}
          className="w-7 h-7 rounded-lg bg-gradient-to-br from-orange-500 to-red-600 text-white flex items-center justify-center hover:opacity-80 transition-opacity"
          title="New chat"
        >
          <i className="fa-solid fa-pen-to-square text-[10px]" />
        </button>
      </div>

      {/* Search bar */}
      <div className="px-3 py-2 border-b border-[#1a1a1a]">
        <div className="relative">
          <i className="fa-solid fa-magnifying-glass absolute left-2.5 top-1/2 -translate-y-1/2 text-[9px] text-[#444]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="w-full bg-[#0d0d0d] border border-[#1a1a1a] rounded-lg pl-7 pr-2 py-1.5 text-[10px] text-[#aaa] placeholder-[#444] focus:outline-none focus:border-[#2a2a2a] transition-colors"
          />
        </div>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto sl-chat-scroll">
        {chatSessions.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full px-4 text-center">
            <i className="fa-solid fa-comments text-2xl text-[#1a1a1a] mb-3" />
            <div className="text-[10px] text-[#444] mb-1">No conversations yet</div>
            <div className="text-[9px] text-[#333] leading-relaxed">
              Start chatting with the AI Agent and your conversations will appear here.
            </div>
          </div>
        )}

        {chatSessions.length > 0 && Object.keys(groupedSessions).length === 0 && (
          <div className="px-4 py-6 text-center text-[10px] text-[#444]">
            No conversations match "{searchQuery}"
          </div>
        )}

        {GROUP_ORDER.map((group) => {
          const sessions = groupedSessions[group];
          if (!sessions || sessions.length === 0) return null;
          return (
            <div key={group} className="mb-1">
              <div className="px-3 py-1.5 text-[8px] font-bold text-[#444] uppercase tracking-wider">
                {group}
              </div>
              {sessions.map((session) => {
                const isActive = session.id === activeChatSessionId;
                return (
                  <div
                    key={session.id}
                    onMouseEnter={() => setHoveredId(session.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onClick={() => loadChatSession(session.id)}
                    className={`group mx-2 px-2.5 py-2 rounded-lg cursor-pointer transition-colors flex items-start gap-2 ${
                      isActive
                        ? 'bg-orange-500/10 border border-orange-500/20'
                        : 'hover:bg-[#111] border border-transparent'
                    }`}
                  >
                    <i
                      className={`fa-solid fa-message text-[9px] mt-0.5 flex-shrink-0 ${
                        isActive ? 'text-orange-500' : 'text-[#333]'
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div
                        className={`text-[10px] truncate leading-tight ${
                          isActive ? 'text-[#ddd] font-medium' : 'text-[#888]'
                        }`}
                      >
                        {session.title}
                      </div>
                      <div className="text-[8px] text-[#3a3a3a] mt-0.5">
                        {formatTime(session.updatedAt)} · {session.messages.length} msgs
                      </div>
                    </div>
                    {hoveredId === session.id && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteChatSession(session.id);
                        }}
                        className="flex-shrink-0 w-5 h-5 rounded hover:bg-[#2a2a2a] text-[#555] hover:text-[#ef4444] flex items-center justify-center transition-colors"
                        title="Delete conversation"
                      >
                        <i className="fa-solid fa-trash text-[8px]" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-[#1a1a1a] flex items-center justify-between">
        <div className="text-[8px] text-[#333] font-mono">
          {chatSessions.length} conversation{chatSessions.length !== 1 ? 's' : ''}
        </div>
        <button
          onClick={() => setChatHistoryCollapsed(true)}
          className="text-[8px] text-[#444] hover:text-[#666] flex items-center gap-1 transition-colors"
        >
          <i className="fa-solid fa-angles-left text-[8px]" /> Collapse
        </button>
      </div>
    </div>
  );
};

export default ChatHistorySidebar;
