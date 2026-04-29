import React, { useState, useEffect, useCallback } from 'react';
import { skillApi } from '../utils/api';

type TabType = 'skills' | 'protocols' | 'evolution';

const MATURITY_COLORS: Record<string, string> = {
  seed: '#6b7280',
  sprout: '#22c55e',
  growing: '#3b82f6',
  mature: '#f59e0b',
  expert: '#ef4444',
  master: '#8b5cf6',
};

const DOMAIN_COLORS: Record<string, string> = {
  code_gen: '#3b82f6',
  world_build: '#22c55e',
  asset_gen: '#f59e0b',
  audio_gen: '#ec4899',
  narrative: '#8b5cf6',
  qa_test: '#06b6d4',
  design: '#f97316',
  optimization: '#14b8a6',
  debug: '#ef4444',
  deploy: '#64748b',
};

const PROTOCOL_STATUS_COLORS: Record<string, string> = {
  proposed: '#6b7280',
  tested: '#3b82f6',
  verified: '#22c55e',
  deprecated: '#9ca3af',
};

const SkillEvolution: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('skills');
  const [skills, setSkills] = useState<any[]>([]);
  const [protocols, setProtocols] = useState<any[]>([]);
  const [evolutions, setEvolutions] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [skillsRes, protocolsRes, evolutionsRes, statsRes] = await Promise.all([
        skillApi.skills(),
        skillApi.protocols(),
        skillApi.evolutionHistory(),
        skillApi.stats(),
      ]);
      setSkills((skillsRes as any)?.skills || (skillsRes as any) || []);
      setProtocols((protocolsRes as any)?.protocols || (protocolsRes as any) || []);
      setEvolutions((evolutionsRes as any)?.evolutions || (evolutionsRes as any) || []);
      setStats(statsRes);
    } catch (e) { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'skills', label: 'Skills', icon: 'fa-bolt' },
    { key: 'protocols', label: 'Debug Protocols', icon: 'fa-bug' },
    { key: 'evolution', label: 'Evolution', icon: 'fa-dna' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#111] text-[#e0e0e0]">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1e1e1e]">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] transition-colors ${
              activeTab === tab.key
                ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                : 'text-[#888] hover:text-[#ccc] hover:bg-[#1a1a1a]'
            }`}
          >
            <i className={`fa-solid ${tab.icon} text-[10px]`} />
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        {stats && (
          <div className="flex items-center gap-3 text-[10px] text-[#666]">
            <span>{stats.total_skills} skills</span>
            <span>{stats.total_protocols} protocols</span>
            <span>{stats.total_evolutions} evolutions</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'skills' && (
          <div className="space-y-2">
            {skills.map((skill: any) => {
              const matColor = MATURITY_COLORS[skill.maturity] || '#666';
              const domColor = DOMAIN_COLORS[skill.domain] || '#666';
              const successRate = skill.success_rate || (skill.usage_count > 0 ? skill.success_count / skill.usage_count : 0);
              return (
                <div key={skill.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: matColor }} />
                    <span className="text-[12px] font-medium">{skill.name}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded" style={{
                      backgroundColor: matColor + '20', color: matColor
                    }}>{skill.maturity}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded" style={{
                      backgroundColor: domColor + '20', color: domColor
                    }}>{skill.domain}</span>
                  </div>
                  <p className="text-[10px] text-[#888] mt-1">{skill.description}</p>
                  <div className="flex items-center gap-3 mt-1.5 text-[10px] text-[#666]">
                    <span>Used: {skill.usage_count}×</span>
                    <span>Success: {(successRate * 100).toFixed(0)}%</span>
                    <span>v{skill.version}</span>
                    {skill.avg_execution_ms > 0 && <span>Avg: {skill.avg_execution_ms.toFixed(0)}ms</span>}
                  </div>
                  <div className="mt-1.5 h-1 bg-[#222] rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{
                      width: `${successRate * 100}%`,
                      backgroundColor: successRate >= 0.8 ? '#22c55e' : successRate >= 0.5 ? '#f59e0b' : '#ef4444'
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'protocols' && (
          <div className="space-y-2">
            {protocols.map((protocol: any) => {
              const statusColor = PROTOCOL_STATUS_COLORS[protocol.status] || '#666';
              return (
                <div key={protocol.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-medium">{protocol.name}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded" style={{
                      backgroundColor: statusColor + '20', color: statusColor
                    }}>{protocol.status}</span>
                    <span className="text-[9px] text-[#555]">confidence: {(protocol.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="mt-1.5 space-y-1">
                    <div className="text-[10px]">
                      <span className="text-red-400">Error: </span>
                      <span className="text-[#888]">{protocol.error_pattern}</span>
                    </div>
                    <div className="text-[10px]">
                      <span className="text-green-400">Fix: </span>
                      <span className="text-[#888]">{protocol.fix_pattern}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5 text-[10px] text-[#666]">
                    <span>Used: {protocol.usage_count}×</span>
                    <span>Success: {protocol.success_count}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'evolution' && (
          <div className="space-y-2">
            {evolutions.length === 0 ? (
              <div className="text-center py-12 text-[#555] text-[12px]">
                <i className="fa-solid fa-dna text-[24px] mb-2 text-[#333]" />
                <p>No evolution events yet</p>
              </div>
            ) : (
              evolutions.map((evo: any) => (
                <div key={evo.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] font-medium">Skill {evo.skill_id}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-900/30 text-purple-400">
                      {evo.evolution_type}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#888] mt-1">{evo.trigger}</div>
                  <div className="flex items-center gap-3 mt-1 text-[10px] text-[#666]">
                    <span>Before: {JSON.stringify(evo.before_state)}</span>
                    <i className="fa-solid fa-arrow-right text-[8px] text-[#555]" />
                    <span>After: {JSON.stringify(evo.after_state)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SkillEvolution;
