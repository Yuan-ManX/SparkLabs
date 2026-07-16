import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface ReputationHistoryEntry {
  entry_id: string;
  faction_id: string;
  change: number;
  reason: string;
  timestamp: string;
  new_score: number;
}

interface TradeModifier {
  modifier_type: string;
  value: number;
  description: string;
}

interface FactionReputation {
  faction_id: string;
  faction_name: string;
  reputation_score: number;
  tier: string;
  history: ReputationHistoryEntry[];
  trade_modifiers: TradeModifier[];
}

const REPUTATION_TIERS = [
  { name: 'hostile', min: -1000, max: -500, color: '#ef4444', icon: '🔥' },
  { name: 'unfriendly', min: -500, max: -100, color: '#f97316', icon: '⚠️' },
  { name: 'neutral', min: -100, max: 100, color: '#888', icon: '➖' },
  { name: 'friendly', min: 100, max: 500, color: '#22c55e', icon: '👍' },
  { name: 'honored', min: 500, max: 1000, color: '#3b82f6', icon: '⭐' },
  { name: 'exalted', min: 1000, max: 3000, color: '#fbbf24', icon: '👑' },
];

const ReputationPanel: React.FC = () => {
  const [factions, setFactions] = useState<FactionReputation[]>([]);
  const [selectedFactionId, setSelectedFactionId] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [deltaAmount, setDeltaAmount] = useState(50);
  const [deltaReason, setDeltaReason] = useState('Quest completion');

  const selectedFaction = factions.find(f => f.faction_id === selectedFactionId);

  const loadFactions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await engineApi.listScenes();
      setFactions([]);
    } catch {
      setFactions([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadFactions(); }, [loadFactions]);

  const getTierForScore = (score: number) => {
    for (const tier of REPUTATION_TIERS) {
      if (score >= tier.min && score < tier.max) return tier;
    }
    return score >= 3000 ? REPUTATION_TIERS[5] : REPUTATION_TIERS[0];
  };

  const getTierProgress = (score: number): number => {
    const tier = getTierForScore(score);
    const range = tier.max - tier.min;
    const offset = score - tier.min;
    return Math.max(0, Math.min(100, (offset / range) * 100));
  };

  const getScoreColor = (score: number): string => {
    if (score >= 500) return '#22c55e';
    if (score >= 100) return '#a3e635';
    if (score >= -100) return '#888';
    if (score >= -500) return '#f97316';
    return '#ef4444';
  };

  const handleAddReputation = () => {
    if (!selectedFactionId) return;
    setFactions(prev =>
      prev.map(faction => {
        if (faction.faction_id !== selectedFactionId) return faction;
        const newScore = faction.reputation_score + deltaAmount;
        const entry: ReputationHistoryEntry = {
          entry_id: `hist_${Date.now()}`,
          faction_id: selectedFactionId,
          change: deltaAmount,
          reason: deltaReason,
          timestamp: new Date().toISOString(),
          new_score: newScore,
        };
        return {
          ...faction,
          reputation_score: newScore,
          tier: getTierForScore(newScore).name,
          history: [entry, ...faction.history].slice(0, 50),
        };
      })
    );
    setMessage(`${deltaAmount > 0 ? '+' : ''}${deltaAmount} reputation with ${selectedFaction?.faction_name}`);
  };

  const handleRemoveReputation = () => {
    setDeltaAmount(prev => -Math.abs(prev));
    handleAddReputation();
    setDeltaAmount(prev => Math.abs(prev));
  };

  const sortedFactions = [...factions].sort((a, b) => b.reputation_score - a.reputation_score);

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#8b5cf6] m-0">Reputation Panel</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <span className="text-[10px] text-[#555]">{factions.length} factions</span>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div className="w-72 border-r border-[#1e1e1e] overflow-y-auto p-3 space-y-2">
          {sortedFactions.map(faction => {
            const tier = getTierForScore(faction.reputation_score);
            return (
              <div
                key={faction.faction_id}
                onClick={() => setSelectedFactionId(faction.faction_id)}
                className="p-3 rounded cursor-pointer transition-colors border"
                style={{
                  backgroundColor: selectedFactionId === faction.faction_id ? tier.color + '15' : '#1a1a2e',
                  borderColor: selectedFactionId === faction.faction_id ? tier.color + '50' : '#2a2a2a',
                }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[14px]">{tier.icon}</span>
                  <span className="text-[12px] font-bold flex-1 truncate">{faction.faction_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className="text-[11px] font-bold"
                    style={{ color: getScoreColor(faction.reputation_score) }}
                  >
                    {faction.reputation_score > 0 ? '+' : ''}{faction.reputation_score}
                  </span>
                  <span
                    className="text-[9px] px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor: tier.color + '20',
                      color: tier.color,
                    }}
                  >
                    {tier.name}
                  </span>
                </div>
                <div className="relative h-1.5 bg-[#111] rounded mt-1.5 overflow-hidden border border-[#2a2a2a]">
                  <div
                    className="absolute top-0 left-0 h-full rounded"
                    style={{
                      width: `${getTierProgress(faction.reputation_score)}%`,
                      backgroundColor: tier.color,
                    }}
                  />
                </div>
              </div>
            );
          })}
          {sortedFactions.length === 0 && (
            <div className="text-center py-8">
              <div className="text-[28px] text-[#333] mb-2">🏛️</div>
              <p className="text-[#555] text-[11px]">No factions loaded</p>
              <p className="text-[#444] text-[10px] mt-0.5">Connect to engine for faction data</p>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto">
          {selectedFaction ? (
            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-[15px] font-bold">{selectedFaction.faction_name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-[#888]">Reputation</span>
                    <span
                      className="text-[13px] font-bold"
                      style={{ color: getScoreColor(selectedFaction.reputation_score) }}
                    >
                      {selectedFaction.reputation_score > 0 ? '+' : ''}{selectedFaction.reputation_score}
                    </span>
                    <span
                      className="text-[9px] px-1.5 py-0.5 rounded"
                      style={{
                        backgroundColor: getTierForScore(selectedFaction.reputation_score).color + '20',
                        color: getTierForScore(selectedFaction.reputation_score).color,
                      }}
                    >
                      {getTierForScore(selectedFaction.reputation_score).name}
                    </span>
                  </div>
                </div>
              </div>

              <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
                <h4 className="text-[11px] font-bold text-[#888] mb-3">Modify Reputation</h4>
                <div className="flex items-center gap-2 mb-2">
                  <input
                    type="number"
                    value={deltaAmount}
                    onChange={e => setDeltaAmount(parseInt(e.target.value) || 0)}
                    className="w-24 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 outline-none"
                  />
                  <input
                    value={deltaReason}
                    onChange={e => setDeltaReason(e.target.value)}
                    placeholder="Reason"
                    className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 outline-none"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleAddReputation}
                    className="flex-1 py-1.5 bg-[#22c55e] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
                  >
                    + Add
                  </button>
                  <button
                    onClick={handleRemoveReputation}
                    className="flex-1 py-1.5 bg-[#ef4444] text-white rounded text-[11px] font-bold border-none cursor-pointer"
                  >
                    - Remove
                  </button>
                </div>
              </div>

              {selectedFaction.trade_modifiers && selectedFaction.trade_modifiers.length > 0 && (
                <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
                  <h4 className="text-[11px] font-bold text-[#888] mb-2">Trade Modifiers</h4>
                  <div className="space-y-1.5">
                    {selectedFaction.trade_modifiers.map((mod, i) => (
                      <div key={i} className="flex items-center justify-between text-[10px]">
                        <span className="text-[#aaa]">{mod.description}</span>
                        <span style={{
                          color: mod.value >= 0 ? '#22c55e' : '#ef4444'
                        }}>
                          {mod.value > 0 ? '+' : ''}{mod.value}{mod.modifier_type === 'percent' ? '%' : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
                <h4 className="text-[11px] font-bold text-[#888] mb-2">
                  Change History ({selectedFaction.history?.length || 0})
                </h4>
                {selectedFaction.history && selectedFaction.history.length > 0 ? (
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {selectedFaction.history.slice(0, 20).map(entry => (
                      <div
                        key={entry.entry_id}
                        className="flex items-center gap-2 py-1 border-b border-[#1e1e1e] text-[10px]"
                      >
                        <span
                          className="w-14 text-right font-bold"
                          style={{
                            color: entry.change >= 0 ? '#22c55e' : '#ef4444'
                          }}
                        >
                          {entry.change > 0 ? '+' : ''}{entry.change}
                        </span>
                        <span className="text-[#aaa] flex-1 truncate">{entry.reason}</span>
                        <span className="text-[#555] text-[9px]">
                          {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : ''}
                        </span>
                        <span className="text-[#666] text-[9px] w-10 text-right">
                          {entry.new_score}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#555] text-[10px] text-center py-4">No history recorded yet</p>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-[32px] text-[#333] mb-3">🏛️</div>
                <p className="text-[#555] text-[12px]">Select a faction to view details</p>
                <p className="text-[#444] text-[10px] mt-1">View reputation tiers, history, and trade modifiers</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReputationPanel;