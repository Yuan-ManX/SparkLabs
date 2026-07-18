"use client";

import React, { useState, useCallback } from 'react';
import {
  Zap, Play, Loader2, AlertTriangle, CheckCircle2,
  Target, Code, GitBranch, Variable, RefreshCw,
} from 'lucide-react';
import { eventSheetApi } from '../utils/api';

type TabId = 'synthesize' | 'events' | 'runtime';

interface Condition {
  property: string;
  operator: string;
  value: any;
  source_phrase: string;
}

interface Action {
  action_type: string;
  target: string;
  parameters: Record<string, any>;
  source_phrase: string;
}

interface EventItem {
  event_id: string;
  event_type: string;
  description: string;
  condition_count: number;
  action_count: number;
  conditions: Condition[];
  actions: Action[];
}

interface SheetData {
  success: boolean;
  sheet_id: string;
  sheet_name: string;
  description: string;
  intent_category: string;
  events: EventItem[];
  variable_count: number;
  coverage_score: number;
  warnings: string[];
  duration_s: number;
  session_id: string;
  error: string | null;
}

interface RuntimeStats {
  sheets: number;
  events: number;
  conditions: number;
  actions: number;
}

const operatorSymbol = (op: string): string => {
  const map: Record<string, string> = {
    less: '<',
    greater: '>',
    equal: '==',
    not_equal: '!=',
    between: 'between',
    contains: 'contains',
  };
  return map[op] || op;
};

const actionColor = (type: string): string => {
  const map: Record<string, string> = {
    spawn_object: 'text-[#6bcb77]',
    play_sound: 'text-[#a855f7]',
    change_scene: 'text-[#00d4ff]',
    set_variable: 'text-[#fdcb6e]',
    send_message: 'text-[#74b9ff]',
    move_object: 'text-[#e94560]',
  };
  return map[type] || 'text-[#888]';
};

const EventSheetPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('synthesize');
  const [prompt, setPrompt] = useState('when health drops below 30, spawn a health potion and play a warning sound; if score rises above 500, change scene to victory');
  const [sheet, setSheet] = useState<SheetData | null>(null);
  const [runtime, setRuntime] = useState<RuntimeStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleSynthesize = useCallback(async () => {
    if (!prompt.trim()) {
      showMessage('Prompt is required', 'error');
      return;
    }
    setIsLoading(true);
    setActiveTab('events');
    try {
      const result = await eventSheetApi.synthesize(prompt) as any;
      const data = result.data || result;
      if (data.success) {
        setSheet(data);
        showMessage(`Synthesized ${data.events.length} events in ${data.duration_s}s`, 'success');
      } else {
        showMessage(data.error || 'Synthesis failed', 'error');
      }
    } catch (err) {
      showMessage('API unavailable - check backend connection', 'error');
    } finally {
      setIsLoading(false);
    }
  }, [prompt]);

  const handleFetchRuntime = useCallback(async () => {
    try {
      const result = await eventSheetApi.runtime() as any;
      const data = result.data || result;
      setRuntime(data);
    } catch (err) {
      setRuntime({ sheets: 0, events: 0, conditions: 0, actions: 0 });
    }
  }, []);

  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'synthesize', label: 'Synthesize', icon: <Zap className="w-3.5 h-3.5" /> },
    { key: 'events', label: 'Events', icon: <GitBranch className="w-3.5 h-3.5" /> },
    { key: 'runtime', label: 'Runtime', icon: <Code className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Zap className="w-[18px] h-[18px] text-[#f97316]" />
          <span className="font-bold text-[15px]">Event Sheet Synthesizer</span>
        </div>
        {sheet && (
          <div className="text-[10px] text-[#666]">
            {sheet.events.length} events · {sheet.variable_count} vars
          </div>
        )}
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
              if (tab.key === 'runtime') handleFetchRuntime();
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
        {/* SYNTHESIZE TAB */}
        {activeTab === 'synthesize' && (
          <div className="flex flex-col gap-3">
            <div>
              <label className="text-[10px] text-[#666] uppercase tracking-wider mb-1.5 block">
                Natural Language Game Logic
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={5}
                placeholder="Describe game logic in plain language..."
                className="w-full bg-[#141414] border border-[#1e1e1e] rounded-lg p-3 text-[12px] text-[#e0e0e0] placeholder-[#444] focus:border-[#f97316]/50 focus:outline-none resize-none"
              />
            </div>

            <button
              onClick={handleSynthesize}
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#f97316]/20 border border-[#f97316]/50 text-[#f97316] rounded-lg text-[12px] font-semibold hover:bg-[#f97316]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              {isLoading ? 'Synthesizing...' : 'Synthesize Event Sheet'}
            </button>

            {sheet && (
              <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="text-[10px] text-[#666] uppercase tracking-wider mb-2">Last Result</div>
                <div className="grid grid-cols-3 gap-2 mb-3">
                  <div className="bg-[#0a0a0a] rounded p-2 text-center">
                    <div className="text-[9px] text-[#555] mb-0.5">Coverage</div>
                    <div className={`text-[18px] font-bold ${
                      sheet.coverage_score >= 0.7 ? 'text-[#6bcb77]' :
                      sheet.coverage_score >= 0.4 ? 'text-[#fdcb6e]' : 'text-[#e94560]'
                    }`}>
                      {(sheet.coverage_score * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="bg-[#0a0a0a] rounded p-2 text-center">
                    <div className="text-[9px] text-[#555] mb-0.5">Events</div>
                    <div className="text-[18px] font-bold text-[#00d4ff]">{sheet.events.length}</div>
                  </div>
                  <div className="bg-[#0a0a0a] rounded p-2 text-center">
                    <div className="text-[9px] text-[#555] mb-0.5">Variables</div>
                    <div className="text-[18px] font-bold text-[#a855f7]">{sheet.variable_count}</div>
                  </div>
                </div>
                <div className="text-[11px] text-[#888]">
                  <span className="text-[#555]">Sheet:</span> {sheet.sheet_name}
                </div>
                <div className="text-[11px] text-[#888]">
                  <span className="text-[#555]">Category:</span> {sheet.intent_category}
                </div>
                {sheet.warnings.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {sheet.warnings.map((w, i) => (
                      <div key={i} className="flex items-start gap-1.5 text-[11px] text-[#fdcb6e]">
                        <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                        <span>{w}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* EVENTS TAB */}
        {activeTab === 'events' && (
          <div className="flex flex-col gap-2">
            {!sheet && (
              <div className="text-center text-[#444] text-[12px] py-8">
                No event sheet yet. Use the Synthesize tab to create one.
              </div>
            )}
            {sheet && sheet.events.map((ev, idx) => (
              <div key={ev.event_id} className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="bg-[#f97316]/20 text-[#f97316] text-[9px] font-bold px-1.5 py-0.5 rounded uppercase">
                    {ev.event_type}
                  </span>
                  <span className="text-[11px] text-[#888] truncate flex-1">{ev.description}</span>
                </div>

                {ev.conditions.length > 0 && (
                  <div className="mb-2">
                    <div className="text-[9px] text-[#555] uppercase tracking-wider mb-1 flex items-center gap-1">
                      <Target className="w-2.5 h-2.5" /> Conditions
                    </div>
                    {ev.conditions.map((c, ci) => (
                      <div key={ci} className="flex items-center gap-2 text-[11px] ml-3 mb-0.5">
                        <span className="text-[#00d4ff] font-mono">{c.property}</span>
                        <span className="text-[#666]">{operatorSymbol(c.operator)}</span>
                        <span className="text-[#fdcb6e] font-mono">{String(c.value)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {ev.actions.length > 0 && (
                  <div>
                    <div className="text-[9px] text-[#555] uppercase tracking-wider mb-1 flex items-center gap-1">
                      <Play className="w-2.5 h-2.5" /> Actions
                    </div>
                    {ev.actions.map((a, ai) => (
                      <div key={ai} className="flex items-center gap-2 text-[11px] ml-3 mb-0.5">
                        <span className={`${actionColor(a.action_type)} font-mono font-semibold`}>
                          {a.action_type}
                        </span>
                        <span className="text-[#666]">→</span>
                        <span className="text-[#e0e0e0] font-mono">{a.target}</span>
                        {Object.keys(a.parameters).length > 0 && (
                          <span className="text-[#555] text-[10px]">
                            ({Object.entries(a.parameters).map(([k, v]) => `${k}=${String(v)}`).join(', ')})
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* RUNTIME TAB */}
        {activeTab === 'runtime' && (
          <div className="flex flex-col gap-3">
            <button
              onClick={handleFetchRuntime}
              className="w-full flex items-center justify-center gap-2 py-2 bg-[#141414] border border-[#1e1e1e] text-[#aaa] rounded-lg text-[12px] hover:border-[#f97316]/30 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Runtime Stats
            </button>

            {runtime && (
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 text-center">
                  <Variable className="w-4 h-4 text-[#f97316] mx-auto mb-1" />
                  <div className="text-[24px] font-bold text-[#f97316]">{runtime.sheets}</div>
                  <div className="text-[10px] text-[#555] uppercase">Sheets</div>
                </div>
                <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 text-center">
                  <GitBranch className="w-4 h-4 text-[#00d4ff] mx-auto mb-1" />
                  <div className="text-[24px] font-bold text-[#00d4ff]">{runtime.events}</div>
                  <div className="text-[10px] text-[#555] uppercase">Events</div>
                </div>
                <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 text-center">
                  <Target className="w-4 h-4 text-[#6bcb77] mx-auto mb-1" />
                  <div className="text-[24px] font-bold text-[#6bcb77]">{runtime.conditions}</div>
                  <div className="text-[10px] text-[#555] uppercase">Conditions</div>
                </div>
                <div className="bg-[#141414] rounded-lg border border-[#1e1e1e] p-3 text-center">
                  <Play className="w-4 h-4 text-[#a855f7] mx-auto mb-1" />
                  <div className="text-[24px] font-bold text-[#a855f7]">{runtime.actions}</div>
                  <div className="text-[10px] text-[#555] uppercase">Actions</div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default EventSheetPanel;
