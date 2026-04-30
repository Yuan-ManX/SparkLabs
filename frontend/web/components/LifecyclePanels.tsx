import React, { useEffect, useState } from 'react';
import { lifecycleApi, slashCommandApi, validationHooksApi } from '../utils/api';

const LifecyclePanel: React.FC = () => {
  const [blueprints, setBlueprints] = useState<Array<Record<string, unknown>>>([]);
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [bpRes, evRes, stRes] = await Promise.all([
          lifecycleApi.blueprints(),
          lifecycleApi.events(),
          lifecycleApi.stats(),
        ]);
        setBlueprints((bpRes as Record<string, unknown>)?.blueprints as Array<Record<string, unknown>> || []);
        setEvents((evRes as Record<string, unknown>)?.events as Array<Record<string, unknown>> || []);
        setStats(stRes as Record<string, unknown>);
      } catch {
        // API not available yet
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleSpawn = async (blueprintName: string) => {
    try {
      await lifecycleApi.spawn(blueprintName);
      const bpRes = await lifecycleApi.blueprints();
      setBlueprints((bpRes as Record<string, unknown>)?.blueprints as Array<Record<string, unknown>> || []);
    } catch {
      // spawn failed
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-[#666]">
        <i className="fa-solid fa-spinner fa-spin mr-2" /> Loading Lifecycle Manager...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#111]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <h2 className="text-[14px] font-semibold text-[#e0e0e0] flex items-center gap-2">
          <i className="fa-solid fa-rotate text-orange-500" /> Agent Lifecycle Manager
        </h2>
        <p className="text-[11px] text-[#666] mt-1">Blueprint-driven agent spawning with Plan-Execute-Reflect cycle</p>
      </div>

      {stats && (
        <div className="grid grid-cols-4 gap-2 px-4 py-2 border-b border-[#1e1e1e]">
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-orange-500">{String(stats.blueprints || 0)}</div>
            <div className="text-[10px] text-[#666]">Blueprints</div>
          </div>
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-[#4ade80]">{String(stats.active_plans || 0)}</div>
            <div className="text-[10px] text-[#666]">Active Plans</div>
          </div>
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-[#fbbf24]">{String(stats.pending_approvals || 0)}</div>
            <div className="text-[10px] text-[#666]">Pending</div>
          </div>
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-[#60a5fa]">{String(stats.total_events || 0)}</div>
            <div className="text-[10px] text-[#666]">Events</div>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <h3 className="text-[12px] font-semibold text-[#aaa] mb-2 uppercase tracking-wider">Agent Blueprints</h3>
        {blueprints.length === 0 ? (
          <div className="text-[#555] text-[12px]">No blueprints available</div>
        ) : (
          <div className="space-y-2">
            {blueprints.map((bp, i) => (
              <div key={i} className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[13px] font-semibold text-[#e0e0e0]">{String(bp.name)}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                    bp.tier === 'director' ? 'bg-orange-500/20 text-orange-500' :
                    bp.tier === 'lead' ? 'bg-blue-500/20 text-blue-500' :
                    bp.tier === 'specialist' ? 'bg-green-500/20 text-green-500' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>
                    {String(bp.tier)}
                  </span>
                </div>
                <p className="text-[11px] text-[#888] mb-2">{String(bp.description || '')}</p>
                <div className="flex items-center gap-3 text-[10px] text-[#666]">
                  <span><i className="fa-solid fa-wrench mr-1" />{String(bp.tool_count || 0)} tools</span>
                  <span><i className="fa-solid fa-star mr-1" />{String(bp.skill_count || 0)} skills</span>
                  <span><i className="fa-solid fa-check mr-1" />{String(bp.verification_count || 0)} checks</span>
                </div>
                <button
                  onClick={() => handleSpawn(String(bp.name))}
                  className="mt-2 text-[11px] px-3 py-1 bg-orange-500/20 text-orange-500 border border-orange-500/30 rounded hover:bg-orange-500/30 transition-colors"
                >
                  <i className="fa-solid fa-plus mr-1" /> Spawn Agent
                </button>
              </div>
            ))}
          </div>
        )}

        <h3 className="text-[12px] font-semibold text-[#aaa] mt-4 mb-2 uppercase tracking-wider">Recent Events</h3>
        {events.length === 0 ? (
          <div className="text-[#555] text-[12px]">No lifecycle events</div>
        ) : (
          <div className="space-y-1">
            {events.slice(0, 20).map((ev, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px] py-1">
                <span className={`w-2 h-2 rounded-full ${
                  (ev.phase as string) === 'spawn' ? 'bg-green-500' :
                  (ev.phase as string) === 'execute' ? 'bg-blue-500' :
                  (ev.phase as string) === 'reflect' ? 'bg-yellow-500' :
                  (ev.phase as string) === 'verify' ? 'bg-purple-500' :
                  'bg-gray-500'
                }`} />
                <span className="text-[#888]">{String(ev.phase)}</span>
                <span className="text-[#666]">agent:{String(ev.agent_id)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const SlashCommandsPanel: React.FC = () => {
  const [commands, setCommands] = useState<Array<Record<string, unknown>>>([]);
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([]);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [input, setInput] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [cmdRes, histRes, stRes] = await Promise.all([
          slashCommandApi.list(selectedCategory || undefined),
          slashCommandApi.history(),
          slashCommandApi.stats(),
        ]);
        setCommands((cmdRes as Record<string, unknown>)?.commands as Array<Record<string, unknown>> || []);
        setHistory((histRes as Record<string, unknown>)?.history as Array<Record<string, unknown>> || []);
        setStats(stRes as Record<string, unknown>);
      } catch {
        // API not available yet
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedCategory]);

  const handleExecute = async () => {
    if (!input.trim()) return;
    try {
      const res = await slashCommandApi.execute(input);
      setResult(res as Record<string, unknown>);
      setInput('');
      const histRes = await slashCommandApi.history();
      setHistory((histRes as Record<string, unknown>)?.history as Array<Record<string, unknown>> || []);
    } catch {
      setResult({ success: false, error: 'Command execution failed' });
    }
  };

  const categories = ['onboarding', 'design', 'art', 'architecture', 'development', 'qa', 'production', 'creative', 'team', 'system'];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-[#666]">
        <i className="fa-solid fa-spinner fa-spin mr-2" /> Loading Slash Commands...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#111]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <h2 className="text-[14px] font-semibold text-[#e0e0e0] flex items-center gap-2">
          <i className="fa-solid fa-terminal text-orange-500" /> Slash Commands
        </h2>
        <p className="text-[11px] text-[#666] mt-1">Workflow-oriented command system for game development</p>
      </div>

      <div className="px-4 py-2 border-b border-[#1e1e1e]">
        <div className="flex gap-1.5">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleExecute(); }}
            className="flex-1 bg-[#0d0d0d] border border-[#2a2a2a] text-[#e0e0e0] text-[13px] px-3 py-2 rounded-lg focus:outline-none focus:border-orange-500/50 placeholder-[#444]"
            placeholder="Type a slash command (e.g. /start template=rpg)"
          />
          <button
            onClick={handleExecute}
            className="px-4 py-2 bg-gradient-to-r from-orange-500 to-red-600 text-white rounded-lg text-[12px] font-semibold hover:opacity-90 transition-all"
          >
            <i className="fa-solid fa-play" />
          </button>
        </div>
      </div>

      {result && (
        <div className={`mx-4 mt-2 p-2 rounded-lg text-[12px] ${
          result.success ? 'bg-green-500/10 border border-green-500/30 text-green-400' : 'bg-red-500/10 border border-red-500/30 text-red-400'
        }`}>
          <pre className="whitespace-pre-wrap">{JSON.stringify(result.output || result.error, null, 2)}</pre>
        </div>
      )}

      <div className="px-4 py-2 border-b border-[#1e1e1e] flex gap-1 flex-wrap">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`text-[10px] px-2 py-1 rounded ${!selectedCategory ? 'bg-orange-500/20 text-orange-500' : 'bg-[#1a1a1a] text-[#888] hover:text-[#aaa]'}`}
        >
          All
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`text-[10px] px-2 py-1 rounded capitalize ${selectedCategory === cat ? 'bg-orange-500/20 text-orange-500' : 'bg-[#1a1a1a] text-[#888] hover:text-[#aaa]'}`}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <div className="space-y-1.5">
          {commands.map((cmd, i) => (
            <div key={i} className="bg-[#1a1a1a] border border-[#2a2a2a] rounded p-2.5 hover:border-[#3a3a3a] transition-colors">
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-semibold text-orange-500">{String(cmd.name)}</span>
                <span className="text-[10px] text-[#666] bg-[#222] px-1.5 py-0.5 rounded">{String(cmd.category)}</span>
              </div>
              <p className="text-[11px] text-[#888] mt-0.5">{String(cmd.description)}</p>
              {Array.isArray(cmd.aliases) && cmd.aliases.length > 0 && (
                <div className="flex gap-1 mt-1">
                  {(cmd.aliases as string[]).map((alias: string, j: number) => (
                    <span key={j} className="text-[9px] px-1.5 py-0.5 bg-[#222] text-[#666] rounded">{alias}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {stats && (
        <div className="px-4 py-2 border-t border-[#1e1e1e] flex items-center gap-4 text-[10px] text-[#666]">
          <span>{String(stats.total_commands)} commands</span>
          <span>{String(stats.total_executions)} executed</span>
          <span>{String(Math.round((stats.success_rate as number || 0) * 100))}% success</span>
        </div>
      )}
    </div>
  );
};

const ValidationHooksPanel: React.FC = () => {
  const [rules, setRules] = useState<Array<Record<string, unknown>>>([]);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [ruleRes, stRes] = await Promise.all([
          validationHooksApi.rules(selectedCategory || undefined),
          validationHooksApi.stats(),
        ]);
        setRules((ruleRes as Record<string, unknown>)?.rules as Array<Record<string, unknown>> || []);
        setStats(stRes as Record<string, unknown>);
      } catch {
        // API not available yet
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedCategory]);

  const handleToggle = async (ruleId: string, enabled: boolean) => {
    try {
      await validationHooksApi.toggleRule(ruleId, !enabled);
      const ruleRes = await validationHooksApi.rules(selectedCategory || undefined);
      setRules((ruleRes as Record<string, unknown>)?.rules as Array<Record<string, unknown>> || []);
    } catch {
      // toggle failed
    }
  };

  const categories = ['safety', 'quality', 'performance', 'workflow', 'general'];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-[#666]">
        <i className="fa-solid fa-spinner fa-spin mr-2" /> Loading Validation Hooks...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#111]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <h2 className="text-[14px] font-semibold text-[#e0e0e0] flex items-center gap-2">
          <i className="fa-solid fa-shield-halved text-orange-500" /> Validation Hooks
        </h2>
        <p className="text-[11px] text-[#666] mt-1">Pre/post execution validation and approval workflows</p>
      </div>

      {stats && (
        <div className="grid grid-cols-4 gap-2 px-4 py-2 border-b border-[#1e1e1e]">
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-orange-500">{String(stats.total_rules || 0)}</div>
            <div className="text-[10px] text-[#666]">Rules</div>
          </div>
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-[#4ade80]">{String(stats.enabled_rules || 0)}</div>
            <div className="text-[10px] text-[#666]">Enabled</div>
          </div>
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-[#fbbf24]">{String(stats.pending_approvals || 0)}</div>
            <div className="text-[10px] text-[#666]">Pending</div>
          </div>
          <div className="bg-[#1a1a1a] rounded p-2 text-center">
            <div className="text-[18px] font-bold text-[#60a5fa]">{Math.round((stats.pass_rate as number || 0) * 100)}%</div>
            <div className="text-[10px] text-[#666]">Pass Rate</div>
          </div>
        </div>
      )}

      <div className="px-4 py-2 border-b border-[#1e1e1e] flex gap-1">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`text-[10px] px-2 py-1 rounded ${!selectedCategory ? 'bg-orange-500/20 text-orange-500' : 'bg-[#1a1a1a] text-[#888] hover:text-[#aaa]'}`}
        >
          All
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`text-[10px] px-2 py-1 rounded capitalize ${selectedCategory === cat ? 'bg-orange-500/20 text-orange-500' : 'bg-[#1a1a1a] text-[#888] hover:text-[#aaa]'}`}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <div className="space-y-1.5">
          {rules.map((rule, i) => (
            <div key={i} className={`bg-[#1a1a1a] border rounded p-2.5 ${rule.enabled ? 'border-[#2a2a2a]' : 'border-[#1e1e1e] opacity-60'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    (rule.severity as string) === 'critical' ? 'bg-red-500' :
                    (rule.severity as string) === 'high' ? 'bg-orange-500' :
                    (rule.severity as string) === 'medium' ? 'bg-yellow-500' :
                    'bg-gray-500'
                  }`} />
                  <span className="text-[12px] font-semibold text-[#e0e0e0]">{String(rule.name)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-[#666] bg-[#222] px-1.5 py-0.5 rounded">{String(rule.phase)}</span>
                  <button
                    onClick={() => handleToggle(String(rule.id), rule.enabled as boolean)}
                    className={`text-[10px] px-2 py-0.5 rounded ${rule.enabled ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}
                  >
                    {rule.enabled ? 'ON' : 'OFF'}
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-[#888] mt-0.5">{String(rule.description)}</p>
              <div className="flex items-center gap-3 mt-1 text-[10px] text-[#666]">
                <span>Action: <span className="text-[#aaa]">{String(rule.action)}</span></span>
                <span>Category: <span className="text-[#aaa]">{String(rule.category)}</span></span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export { LifecyclePanel, SlashCommandsPanel, ValidationHooksPanel };
export default LifecyclePanel;
