"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Dna, Play, Loader2, CheckCircle2, AlertTriangle,
  Zap, Palette, Gauge, Users, ArrowDownUp, RefreshCw,
} from 'lucide-react';
import { gameMutatorApi } from '../utils/api';

type TabId = 'strategies' | 'mutate' | 'history';

interface Strategy {
  strategy_id: string;
  name: string;
  description: string;
  category: string;
}

interface ParamPair {
  original_params: Record<string, any> | null;
  variant_params: Record<string, any> | null;
  changes: string[];
}

const categoryIcon = (cat: string): React.ReactNode => {
  switch (cat) {
    case 'difficulty': return <Zap className="w-3 h-3" />;
    case 'visual': return <Palette className="w-3 h-3" />;
    case 'pace': return <Gauge className="w-3 h-3" />;
    case 'density': return <Users className="w-3 h-3" />;
    case 'mechanic': return <ArrowDownUp className="w-3 h-3" />;
    default: return <Dna className="w-3 h-3" />;
  }
};

const categoryColor = (cat: string): string => {
  switch (cat) {
    case 'difficulty': return 'text-[#e94560] bg-[#e94560]/10 border-[#e94560]/30';
    case 'visual': return 'text-[#a855f7] bg-[#a855f7]/10 border-[#a855f7]/30';
    case 'pace': return 'text-[#00d4ff] bg-[#00d4ff]/10 border-[#00d4ff]/30';
    case 'density': return 'text-[#6bcb77] bg-[#6bcb77]/10 border-[#6bcb77]/30';
    case 'mechanic': return 'text-[#fdcb6e] bg-[#fdcb6e]/10 border-[#fdcb6e]/30';
    default: return 'text-[#888] bg-[#444]/10 border-[#444]/30';
  }
};

const GameMutatorPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('strategies');
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [htmlInput, setHtmlInput] = useState('');
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStrategies = useCallback(async () => {
    try {
      const res = await gameMutatorApi.strategies() as any;
      const data = res.data || res;
      if (Array.isArray(data) && data.length > 0) {
        setStrategies(data);
        if (!selectedStrategy) setSelectedStrategy(data[0].strategy_id);
      }
    } catch {
      setStrategies([]);
    }
  }, [selectedStrategy]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await gameMutatorApi.history() as any;
      const data = res.data || res;
      setHistory(Array.isArray(data) ? data : []);
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const handleMutate = useCallback(async () => {
    if (!htmlInput.trim()) {
      showMessage('Game HTML is required', 'error');
      return;
    }
    if (!selectedStrategy) {
      showMessage('Select a mutation strategy', 'error');
      return;
    }
    setIsLoading(true);
    try {
      const res = await gameMutatorApi.mutate(htmlInput, selectedStrategy) as any;
      const data = res.data || res;
      if (data.success) {
        setResult(data);
        showMessage(`Mutation applied: ${data.changes.length} changes`, 'success');
      } else {
        showMessage(data.error || 'Mutation failed', 'error');
      }
    } catch {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [htmlInput, selectedStrategy]);

  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'strategies', label: 'Strategies', icon: <Dna className="w-3.5 h-3.5" /> },
    { key: 'mutate', label: 'Mutate', icon: <Play className="w-3.5 h-3.5" /> },
    { key: 'history', label: 'History', icon: <RefreshCw className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Dna className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">Game Mutation Engine</span>
        </div>
        <div className="text-[10px] text-[#666]">
          {strategies.length} strategies
        </div>
      </div>

      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#6bcb77]/10 border-[#6bcb77]/30 text-[#6bcb77]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#1e1e1e]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#1e1e1e]">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => {
              setActiveTab(tab.key);
              if (tab.key === 'history') fetchHistory();
            }}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors ${
              activeTab === tab.key
                ? 'bg-[#141414] text-[#f97316] border-b-2 border-[#f97316]'
                : 'text-[#666] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-3">
        {/* STRATEGIES TAB */}
        {activeTab === 'strategies' && (
          <div className="flex flex-col gap-2">
            {strategies.length === 0 && (
              <div className="text-center text-[#444] text-[12px] py-8">
                Loading strategies...
              </div>
            )}
            {strategies.map(s => (
              <button
                key={s.strategy_id}
                onClick={() => {
                  setSelectedStrategy(s.strategy_id);
                  setActiveTab('mutate');
                }}
                className={`text-left bg-[#141414] rounded-lg border p-3 transition-all hover:border-[#f97316]/30 ${
                  selectedStrategy === s.strategy_id ? 'border-[#f97316]/50' : 'border-[#1e1e1e]'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${categoryColor(s.category)}`}>
                    {categoryIcon(s.category)}
                    {s.category}
                  </span>
                  <span className="text-[12px] font-semibold text-[#e0e0e0]">{s.name}</span>
                </div>
                <div className="text-[11px] text-[#888]">{s.description}</div>
              </button>
            ))}
          </div>
        )}

        {/* MUTATE TAB */}
        {activeTab === 'mutate' && (
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wider mb-1.5 block">
                Mutation Strategy
              </label>
              <select
                value={selectedStrategy}
                onChange={(e) => setSelectedStrategy(e.target.value)}
                className="w-full bg-[#141414] border border-[#1e1e1e] rounded-lg p-2 text-[12px] text-[#e0e0e0] focus:border-[#f97316]/50 focus:outline-none"
              >
                {strategies.map(s => (
                  <option key={s.strategy_id} value={s.strategy_id}>
                    {s.name} ({s.category})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wider mb-1.5 block">
                Game HTML
              </label>
              <textarea
                value={htmlInput}
                onChange={(e) => setHtmlInput(e.target.value)}
                rows={4}
                placeholder="Paste game HTML here, or it will be auto-filled from the conductor..."
                className="w-full bg-[#141414] border border-[#1e1e1e] rounded-lg p-2 text-[11px] text-[#e0e0e0] placeholder-[#444] focus:border-[#f97316]/50 focus:outline-none resize-none font-mono"
              />
            </div>

            <button
              onClick={handleMutate}
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#f97316]/20 border border-[#f97316]/50 text-[#f97316] rounded-lg text-[12px] font-semibold hover:bg-[#f97316]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {isLoading ? 'Mutating...' : 'Apply Mutation'}
            </button>

            {result && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle2 className="w-4 h-4 text-[#6bcb77]" />
                  <span className="text-[12px] font-semibold">
                    {result.strategy?.name || 'Mutation Applied'}
                  </span>
                </div>

                {/* Changes list */}
                <div className="text-[9px] text-[#555] uppercase tracking-wider mb-1">Changes</div>
                <div className="space-y-1 mb-3">
                  {result.changes?.map((c: string, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-[11px] font-mono ml-2">
                      <ArrowDownUp className="w-2.5 h-2.5 text-[#f97316] flex-shrink-0" />
                      <span className="text-[#aaa]">{c}</span>
                    </div>
                  ))}
                </div>

                {/* Param comparison */}
                {result.original_params && result.variant_params && (
                  <>
                  <div className="text-[9px] text-[#555] uppercase tracking-wider mb-1">Parameter Comparison</div>
                  <div className="grid grid-cols-3 gap-1 text-[10px] font-mono">
                    <div className="text-[#666]">Param</div>
                    <div className="text-[#888]">Original</div>
                    <div className="text-[#f97316]">Variant</div>
                    {Object.keys(result.original_params).map(k => (
                      <React.Fragment key={k}>
                        <div className="text-[#666]">{k}</div>
                        <div className="text-[#888]">{String(result.original_params[k])}</div>
                        <div className="text-[#f97316]">{String(result.variant_params[k])}</div>
                      </React.Fragment>
                    ))}
                  </div>
                  </>
                )}

                <div className="mt-2 text-[10px] text-[#555]">
                  Variant HTML: {(result.variant_html_length / 1024).toFixed(1)}KB
                </div>
              </div>
            )}
          </div>
        )}

        {/* HISTORY TAB */}
        {activeTab === 'history' && (
          <div className="flex flex-col gap-2">
            {history.length === 0 && (
              <div className="text-center text-[#444] text-[12px] py-8">
                No mutation history yet.
              </div>
            )}
            {history.map((h, i) => (
              <div key={i} className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-2.5">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`inline-flex items-center gap-1 text-[8px] font-bold px-1 py-0.5 rounded border uppercase ${categoryColor(h.strategy?.category || '')}`}>
                    {categoryIcon(h.strategy?.category || '')}
                    {h.strategy?.category || 'unknown'}
                  </span>
                  <span className="text-[11px] font-semibold">{h.strategy?.name || 'Unknown'}</span>
                </div>
                <div className="text-[10px] text-[#666]">
                  {h.changes?.length || 0} changes · {(h.variant_html_length / 1024).toFixed(1)}KB · {h.duration_s}s
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default GameMutatorPanel;
