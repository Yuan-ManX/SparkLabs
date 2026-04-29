import React, { useState, useCallback, useRef, useEffect } from 'react';

interface AIPromptBarProps {
  onPrompt: (prompt: string) => void;
  onQuickAction: (action: string) => void;
  isGenerating: boolean;
}

const QUICK_ACTIONS = [
  { id: 'world', label: 'Generate World', icon: 'fa-globe', color: '#22c55e' },
  { id: 'character', label: 'Create Character', icon: 'fa-user', color: '#3b82f6' },
  { id: 'mechanic', label: 'Add Mechanic', icon: 'fa-gears', color: '#f59e0b' },
  { id: 'level', label: 'Build Level', icon: 'fa-layer-group', color: '#8b5cf6' },
  { id: 'dialogue', label: 'Write Dialogue', icon: 'fa-comments', color: '#ec4899' },
  { id: 'fix', label: 'Fix Issues', icon: 'fa-wrench', color: '#ef4444' },
];

const SUGGESTIONS = [
  'Create a fantasy RPG with turn-based combat',
  'Build a platformer with gravity mechanics',
  'Design a puzzle game with color matching',
  'Generate a space shooter with power-ups',
  'Make a farming simulation with day/night cycle',
];

const AIPromptBar: React.FC<AIPromptBarProps> = ({ onPrompt, onQuickAction, isGenerating }) => {
  const [prompt, setPrompt] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showQuickActions, setShowQuickActions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !isGenerating) {
      onPrompt(prompt.trim());
      setPrompt('');
      setShowSuggestions(false);
    }
  }, [prompt, isGenerating, onPrompt]);

  const handleSuggestionClick = useCallback((suggestion: string) => {
    setPrompt(suggestion);
    setShowSuggestions(false);
    inputRef.current?.focus();
  }, []);

  const handleQuickAction = useCallback((actionId: string) => {
    onQuickAction(actionId);
    setShowQuickActions(false);
  }, [onQuickAction]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setShowSuggestions(true);
      }
      if (e.key === 'Escape') {
        setShowSuggestions(false);
        setShowQuickActions(false);
        inputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="relative">
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <div className="relative flex-1">
          <div className="flex items-center bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg px-3 py-2 gap-2 focus-within:border-orange-500/50 transition-colors">
            <i className={`fa-solid ${isGenerating ? 'fa-spinner fa-spin' : 'fa-wand-magic-sparkles'} text-[11px] text-orange-500`} />
            <input
              ref={inputRef}
              type="text"
              placeholder="Describe what you want to create... (Ctrl+K)"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              className="flex-1 bg-transparent text-[12px] text-[#ddd] outline-none placeholder-[#444]"
              disabled={isGenerating}
            />
            <button
              type="button"
              onClick={() => setShowQuickActions(!showQuickActions)}
              className="text-[10px] text-[#555] hover:text-[#888] px-1.5 py-0.5 bg-[#1a1a1a] rounded border border-[#2a2a2a]"
            >
              <i className="fa-solid fa-bolt text-[8px]" /> Quick
            </button>
          </div>
          {showSuggestions && !prompt && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-[#161616] border border-[#2a2a2a] rounded-lg z-50 shadow-xl overflow-hidden" style={{ animation: 'fade-in 0.15s ease-out' }}>
              <div className="px-3 py-1.5 text-[9px] font-bold text-[#444] uppercase tracking-wider border-b border-[#1e1e1e]">
                Suggestions
              </div>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onMouseDown={() => handleSuggestionClick(s)}
                  className="w-full text-left px-3 py-2 text-[11px] text-[#888] hover:bg-[#1a1a1a] hover:text-[#ddd] transition-colors flex items-center gap-2"
                >
                  <i className="fa-solid fa-sparkles text-[9px] text-orange-500/50" />
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          type="submit"
          disabled={!prompt.trim() || isGenerating}
          className="px-4 py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          <i className="fa-solid fa-paper-plane text-[10px]" />
          Generate
        </button>
      </form>
      {showQuickActions && (
        <div className="absolute top-full left-0 mt-1 bg-[#161616] border border-[#2a2a2a] rounded-lg z-50 shadow-xl p-2 min-w-[200px]" style={{ animation: 'fade-in 0.15s ease-out' }}>
          <div className="text-[9px] font-bold text-[#444] uppercase tracking-wider px-2 py-1 mb-1">Quick Actions</div>
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.id}
              onMouseDown={() => handleQuickAction(action.id)}
              className="w-full text-left px-2 py-1.5 text-[11px] text-[#888] hover:bg-[#1a1a1a] hover:text-[#ddd] rounded flex items-center gap-2 transition-colors"
            >
              <i className={`fa-solid ${action.icon} text-[10px]`} style={{ color: action.color }} />
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default AIPromptBar;
