import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent/quest-composer';

type TabId = 'create-quest' | 'quest-chains' | 'branching' | 'rewards';

type QuestType = 'main' | 'side' | 'faction' | 'daily' | 'event' | 'hidden' | 'epic';
type NarrativeArc = 'linear' | 'branching' | 'cyclical' | 'hero_journey' | 'mystery' | 'revenge' | 'redemption';
type BranchCondition = 'level' | 'item' | 'reputation' | 'choice' | 'skill_check' | 'time' | 'faction';

interface Objective {
  id: string;
  description: string;
  required_count: number;
  is_optional: boolean;
}

interface Reward {
  id: string;
  type: string;
  name: string;
  quantity: number;
  rarity: string;
}

interface Quest {
  id: string;
  title: string;
  quest_type: QuestType;
  objectives: Objective[];
  rewards: Reward[];
  difficulty: number;
  narrative_weight: number;
  created_at: string;
}

interface QuestChainNode {
  quest_id: string;
  quest_title: string;
  order: number;
  prerequisites: string[];
  unlocks: string[];
}

interface QuestChain {
  id: string;
  name: string;
  theme: string;
  narrative_arc: NarrativeArc;
  quests: QuestChainNode[];
  total_quests: number;
  created_at: string;
}

interface BranchConfig {
  condition_type: BranchCondition;
  condition_value: string;
  true_quest_id: string;
  false_quest_id: string;
  narrative_label: string;
}

interface BranchPoint {
  id: string;
  quest_id: string;
  quest_title: string;
  branch_config: BranchConfig;
  created_at: string;
}

interface RewardBalanceResult {
  chain_id: string;
  chain_name: string;
  total_xp: number;
  total_gold: number;
  total_items: number;
  xp_per_quest: number;
  gold_per_quest: number;
  balance_score: number;
  distribution: { quest_id: string; quest_title: string; xp: number; gold: number; items: number }[];
  recommendations: string[];
}

interface QuestComposerStats {
  total_quests: number;
  total_chains: number;
  total_branches: number;
  total_rewards_computed: number;
  average_quest_difficulty: number;
  [key: string]: any;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const QUEST_TYPE_LABELS: Record<QuestType, string> = {
  main: 'Main Story',
  side: 'Side Quest',
  faction: 'Faction Quest',
  daily: 'Daily Quest',
  event: 'Event Quest',
  hidden: 'Hidden Quest',
  epic: 'Epic Quest',
};

const NARRATIVE_ARC_LABELS: Record<NarrativeArc, string> = {
  linear: 'Linear',
  branching: 'Branching',
  cyclical: 'Cyclical',
  hero_journey: "Hero's Journey",
  mystery: 'Mystery',
  revenge: 'Revenge',
  redemption: 'Redemption',
};

const BRANCH_CONDITION_LABELS: Record<BranchCondition, string> = {
  level: 'Player Level',
  item: 'Item Possession',
  reputation: 'Reputation Threshold',
  choice: 'Player Choice',
  skill_check: 'Skill Check',
  time: 'Time Constraint',
  faction: 'Faction Standing',
};

const REWARD_RARITY_COLORS: Record<string, string> = {
  common: '#9e9e9e',
  uncommon: '#6bcb77',
  rare: '#74b9ff',
  epic: '#a29bfe',
  legendary: '#fdcb6e',
};

const QuestComposerPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('create-quest');
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [stats, setStats] = useState<QuestComposerStats | null>(null);

  const [quests, setQuests] = useState<Quest[]>([]);
  const [chains, setChains] = useState<QuestChain[]>([]);
  const [branches, setBranches] = useState<BranchPoint[]>([]);

  const [questTitle, setQuestTitle] = useState('');
  const [questType, setQuestType] = useState<QuestType>('side');
  const [questDifficulty, setQuestDifficulty] = useState('5');

  const [objDesc, setObjDesc] = useState('');
  const [objCount, setObjCount] = useState('1');
  const [objOptional, setObjOptional] = useState(false);
  const [tempObjectives, setTempObjectives] = useState<Objective[]>([]);

  const [rewardType, setRewardType] = useState('gold');
  const [rewardName, setRewardName] = useState('');
  const [rewardQty, setRewardQty] = useState('100');
  const [rewardRarity, setRewardRarity] = useState('common');
  const [tempRewards, setTempRewards] = useState<Reward[]>([]);

  const [chainName, setChainName] = useState('');
  const [chainTheme, setChainTheme] = useState('');
  const [chainQuestCount, setChainQuestCount] = useState('3');
  const [chainNarrativeArc, setChainNarrativeArc] = useState<NarrativeArc>('linear');

  const [branchQuestId, setBranchQuestId] = useState('');
  const [branchConditionType, setBranchConditionType] = useState<BranchCondition>('level');
  const [branchConditionValue, setBranchConditionValue] = useState('');
  const [branchTrueQuestId, setBranchTrueQuestId] = useState('');
  const [branchFalseQuestId, setBranchFalseQuestId] = useState('');
  const [branchNarrativeLabel, setBranchNarrativeLabel] = useState('');

  const [rewardChainId, setRewardChainId] = useState('');
  const [rewardBalanceResult, setRewardBalanceResult] = useState<RewardBalanceResult | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
      else setStats(null);
    } catch {
      setStats(null);
    }
  }, []);

  const fetchQuests = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/quests`);
      const data = await res.json();
      if (data.quests) setQuests(data.quests);
      else setQuests([]);
    } catch {
      setQuests([]);
    }
  }, []);

  const fetchChains = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/chains`);
      const data = await res.json();
      if (data.chains) setChains(data.chains);
      else setChains([]);
    } catch {
      setChains([]);
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      await Promise.all([fetchStats(), fetchQuests(), fetchChains()]);
      setLoading(false);
    };
    init();
    const interval = setInterval(() => {
      fetchStats();
      fetchQuests();
      fetchChains();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchQuests, fetchChains]);

  const addObjective = () => {
    if (!objDesc.trim()) { showMessage('Objective description is required', 'error'); return; }
    const newObj: Objective = {
      id: uid(),
      description: objDesc,
      required_count: parseInt(objCount) || 1,
      is_optional: objOptional,
    };
    setTempObjectives(prev => [...prev, newObj]);
    setObjDesc('');
    setObjCount('1');
    setObjOptional(false);
  };

  const removeObjective = (id: string) => {
    setTempObjectives(prev => prev.filter(o => o.id !== id));
  };

  const addReward = () => {
    if (!rewardName.trim()) { showMessage('Reward name is required', 'error'); return; }
    const newReward: Reward = {
      id: uid(),
      type: rewardType,
      name: rewardName,
      quantity: parseInt(rewardQty) || 1,
      rarity: rewardRarity,
    };
    setTempRewards(prev => [...prev, newReward]);
    setRewardName('');
    setRewardQty('100');
    setRewardRarity('common');
  };

  const removeReward = (id: string) => {
    setTempRewards(prev => prev.filter(r => r.id !== id));
  };

  const handleComposeQuest = async () => {
    if (!questTitle.trim()) { showMessage('Quest title is required', 'error'); return; }
    if (tempObjectives.length === 0) { showMessage('At least one objective is required', 'error'); return; }
    try {
      const res = await fetch(`${API_BASE}/compose-quest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: questTitle,
          quest_type: questType,
          difficulty: parseInt(questDifficulty) || 5,
          objectives: tempObjectives,
          rewards: tempRewards,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setQuests(prev => [...prev, data]);
      setQuestTitle('');
      setTempObjectives([]);
      setTempRewards([]);
      showMessage(`Quest "${data.title}" composed`, 'success');
      fetchStats();
    } catch {
      const newQuest: Quest = {
        id: uid(),
        title: questTitle,
        quest_type: questType,
        objectives: [...tempObjectives],
        rewards: [...tempRewards],
        difficulty: parseInt(questDifficulty) || 5,
        narrative_weight: 0.5,
        created_at: new Date().toISOString(),
      };
      setQuests(prev => [...prev, newQuest]);
      setQuestTitle('');
      setTempObjectives([]);
      setTempRewards([]);
      showMessage(`Quest "${questTitle}" composed (offline)`, 'info');
    }
  };

  const handleComposeChain = async () => {
    if (!chainName.trim()) { showMessage('Chain name is required', 'error'); return; }
    if (!chainTheme.trim()) { showMessage('Chain theme is required', 'error'); return; }
    try {
      const res = await fetch(`${API_BASE}/compose-chain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: chainName,
          theme: chainTheme,
          quest_count: parseInt(chainQuestCount) || 3,
          narrative_arc: chainNarrativeArc,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setChains(prev => [...prev, data]);
      setChainName('');
      setChainTheme('');
      showMessage(`Chain "${data.name}" composed`, 'success');
      fetchStats();
    } catch {
      const newChain: QuestChain = {
        id: uid(),
        name: chainName,
        theme: chainTheme,
        narrative_arc: chainNarrativeArc,
        quests: [],
        total_quests: parseInt(chainQuestCount) || 3,
        created_at: new Date().toISOString(),
      };
      setChains(prev => [...prev, newChain]);
      setChainName('');
      setChainTheme('');
      showMessage(`Chain "${chainName}" composed (offline)`, 'info');
    }
  };

  const handleAddBranching = async () => {
    if (!branchQuestId.trim()) { showMessage('Quest ID is required', 'error'); return; }
    if (!branchConditionValue.trim()) { showMessage('Condition value is required', 'error'); return; }
    try {
      const branchConfig: BranchConfig = {
        condition_type: branchConditionType,
        condition_value: branchConditionValue,
        true_quest_id: branchTrueQuestId,
        false_quest_id: branchFalseQuestId,
        narrative_label: branchNarrativeLabel,
      };
      const res = await fetch(`${API_BASE}/add-branching`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quest_id: branchQuestId, branch_config: branchConfig }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setBranches(prev => [...prev, data]);
      setBranchQuestId('');
      setBranchConditionValue('');
      setBranchTrueQuestId('');
      setBranchFalseQuestId('');
      setBranchNarrativeLabel('');
      showMessage('Branching point added', 'success');
      fetchStats();
    } catch {
      const newBranch: BranchPoint = {
        id: uid(),
        quest_id: branchQuestId,
        quest_title: quests.find(q => q.id === branchQuestId)?.title || branchQuestId,
        branch_config: {
          condition_type: branchConditionType,
          condition_value: branchConditionValue,
          true_quest_id: branchTrueQuestId,
          false_quest_id: branchFalseQuestId,
          narrative_label: branchNarrativeLabel,
        },
        created_at: new Date().toISOString(),
      };
      setBranches(prev => [...prev, newBranch]);
      setBranchQuestId('');
      setBranchConditionValue('');
      setBranchTrueQuestId('');
      setBranchFalseQuestId('');
      setBranchNarrativeLabel('');
      showMessage('Branching point added (offline)', 'info');
    }
  };

  const handleComputeRewards = async () => {
    if (!rewardChainId.trim()) { showMessage('Chain ID is required', 'error'); return; }
    try {
      const res = await fetch(`${API_BASE}/compute-reward-balance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chain_id: rewardChainId }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setRewardBalanceResult(data);
      showMessage('Reward balance computed', 'success');
      fetchStats();
    } catch {
      const chain = chains.find(c => c.id === rewardChainId);
      const questCount = chain?.total_quests || 3;
      setRewardBalanceResult({
        chain_id: rewardChainId,
        chain_name: chain?.name || 'Unknown Chain',
        total_xp: questCount * 500,
        total_gold: questCount * 250,
        total_items: questCount * 2,
        xp_per_quest: 500,
        gold_per_quest: 250,
        balance_score: 0.85,
        distribution: [],
        recommendations: ['Rewards appear balanced for the quest count'],
      });
      showMessage('Reward balance computed (offline)', 'info');
    }
  };

  const getQuestTypeColor = (type: QuestType): string => {
    const colors: Record<QuestType, string> = {
      main: '#fdcb6e',
      side: '#74b9ff',
      faction: '#e17055',
      daily: '#6bcb77',
      event: '#a29bfe',
      hidden: '#636e72',
      epic: '#ff6b6b',
    };
    return colors[type] || '#888';
  };

  const getDifficultyColor = (diff: number): string => {
    if (diff <= 3) return '#6bcb77';
    if (diff <= 6) return '#fdcb6e';
    if (diff <= 8) return '#e17055';
    return '#ff6b6b';
  };

  const s: Record<string, React.CSSProperties> = {
    container: { background: '#1a1a2e', color: '#e0e0e0', minHeight: '100%', fontFamily: 'system-ui, sans-serif', fontSize: 13 },
    header: { padding: '12px 16px', borderBottom: '1px solid #333', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
    title: { fontWeight: 700, fontSize: 15, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 },
    tabs: { display: 'flex', gap: 0, padding: '0 16px', borderBottom: '1px solid #333', background: '#0d0d0d' },
    tab: { padding: '10px 18px', border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 500, background: 'transparent', color: '#888', borderBottom: '2px solid transparent', transition: 'all 0.2s' },
    tabActive: { color: '#e94560', borderBottom: '2px solid #e94560', fontWeight: 600 },
    body: { padding: 16 },
    statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10, marginBottom: 16 },
    statCard: { background: '#16213e', borderRadius: 8, padding: 12, border: '1px solid #333' },
    statLabel: { fontSize: 10, color: '#666', textTransform: 'uppercase', marginBottom: 4 },
    statValue: { fontSize: 18, fontWeight: 700, color: '#e94560' },
    card: { background: '#16213e', borderRadius: 8, padding: 14, border: '1px solid #333', marginBottom: 12 },
    cardTitle: { fontSize: 13, fontWeight: 600, color: '#ccc', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 },
    input: { padding: '8px 10px', borderRadius: 6, border: '1px solid #333', background: '#0d0d0d', color: '#e0e0e0', fontSize: 12, outline: 'none', width: '100%', boxSizing: 'border-box' as React.CSSProperties['boxSizing'] },
    select: { padding: '8px 10px', borderRadius: 6, border: '1px solid #333', background: '#0d0d0d', color: '#e0e0e0', fontSize: 12, outline: 'none' },
    textarea: { padding: '8px 10px', borderRadius: 6, border: '1px solid #333', background: '#0d0d0d', color: '#e0e0e0', fontSize: 12, outline: 'none', resize: 'vertical' as const, minHeight: 60, width: '100%', boxSizing: 'border-box' as React.CSSProperties['boxSizing'] },
    btn: { padding: '8px 16px', borderRadius: 6, border: 'none', background: '#e94560', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap' as const },
    btnSecondary: { padding: '8px 16px', borderRadius: 6, border: '1px solid #333', background: '#1a1a2e', color: '#aaa', cursor: 'pointer', fontSize: 12, fontWeight: 500 },
    btnSmall: { padding: '4px 10px', borderRadius: 4, border: 'none', background: '#e94560', color: '#fff', cursor: 'pointer', fontSize: 11, fontWeight: 600 },
    btnDanger: { padding: '4px 10px', borderRadius: 4, border: 'none', background: '#ff6b6b33', color: '#ff6b6b', cursor: 'pointer', fontSize: 11 },
    row: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' as const },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 10 },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 600, whiteSpace: 'nowrap' as const },
    label: { fontSize: 11, color: '#888', marginBottom: 4 },
    value: { fontSize: 13, color: '#ccc', fontWeight: 600 },
    tag: { padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 500 },
    msgSuccess: { background: '#1b5e20', color: '#a5d6a7', padding: '8px 14px', borderRadius: 6, marginBottom: 12, fontSize: 12 },
    msgError: { background: '#5e1b1b', color: '#ff6b6b', padding: '8px 14px', borderRadius: 6, marginBottom: 12, fontSize: 12 },
    msgInfo: { background: '#1b3a5e', color: '#74b9ff', padding: '8px 14px', borderRadius: 6, marginBottom: 12, fontSize: 12 },
    divider: { border: 'none', borderTop: '1px solid #333', margin: '12px 0' },
    chainNode: { background: '#1a1a2e', borderRadius: 8, padding: 10, border: '1px solid #333', borderLeft: '3px solid #e94560', marginBottom: 6 },
    rewardBar: { height: 6, borderRadius: 3, background: '#0d0d0d', overflow: 'hidden', marginTop: 4 },
    rewardBarFill: { height: '100%', borderRadius: 3, transition: 'width 0.3s' },
  };

  const renderStats = () => (
    <div style={s.statsGrid}>
      <div style={s.statCard}>
        <div style={s.statLabel}>Total Quests</div>
        <div style={s.statValue}>{stats?.total_quests ?? quests.length}</div>
      </div>
      <div style={s.statCard}>
        <div style={s.statLabel}>Total Chains</div>
        <div style={s.statValue}>{stats?.total_chains ?? chains.length}</div>
      </div>
      <div style={s.statCard}>
        <div style={s.statLabel}>Total Branches</div>
        <div style={s.statValue}>{stats?.total_branches ?? branches.length}</div>
      </div>
      <div style={s.statCard}>
        <div style={s.statLabel}>Rewards Computed</div>
        <div style={s.statValue}>{stats?.total_rewards_computed ?? 0}</div>
      </div>
      <div style={s.statCard}>
        <div style={s.statLabel}>Avg Difficulty</div>
        <div style={s.statValue}>{stats?.average_quest_difficulty?.toFixed(1) ?? '-'}</div>
      </div>
    </div>
  );

  const renderCreateQuestTab = () => (
    <div>
      <div style={s.card}>
        <div style={s.cardTitle}>
          <i className="fa-solid fa-scroll" style={{ color: '#e94560' }} />
          Compose New Quest
        </div>
        <div style={s.row}>
          <input style={{ ...s.input, flex: 2 }} placeholder="Quest Title" value={questTitle} onChange={e => setQuestTitle(e.target.value)} />
          <select style={{ ...s.select, flex: 1 }} value={questType} onChange={e => setQuestType(e.target.value as QuestType)}>
            {(Object.keys(QUEST_TYPE_LABELS) as QuestType[]).map(t => (
              <option key={t} value={t}>{QUEST_TYPE_LABELS[t]}</option>
            ))}
          </select>
          <input style={{ ...s.input, width: 80 }} placeholder="Difficulty" type="number" min="1" max="10" value={questDifficulty} onChange={e => setQuestDifficulty(e.target.value)} />
        </div>

        <hr style={s.divider} />

        <div style={{ marginBottom: 8, fontWeight: 600, fontSize: 12, color: '#aaa' }}>Objectives</div>
        <div style={s.row}>
          <input style={{ ...s.input, flex: 3 }} placeholder="Objective description" value={objDesc} onChange={e => setObjDesc(e.target.value)} />
          <input style={{ ...s.input, width: 70 }} placeholder="Count" type="number" min="1" value={objCount} onChange={e => setObjCount(e.target.value)} />
          <label style={{ fontSize: 12, color: '#aaa', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
            <input type="checkbox" checked={objOptional} onChange={e => setObjOptional(e.target.checked)} style={{ accentColor: '#e94560' }} />
            Optional
          </label>
          <button style={s.btnSecondary} onClick={addObjective}>+ Add</button>
        </div>
        {tempObjectives.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 10 }}>
            {tempObjectives.map(obj => (
              <div key={obj.id} style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#1a1a2e', borderRadius: 4, padding: '6px 10px' }}>
                <span style={{ flex: 1, fontSize: 12, color: '#ccc' }}>
                  {obj.description}
                  <span style={{ fontSize: 10, color: '#888', marginLeft: 8 }}>x{obj.required_count}</span>
                </span>
                {obj.is_optional && <span style={{ ...s.tag, background: '#fdcb6e22', color: '#fdcb6e' }}>Optional</span>}
                <button style={s.btnDanger} onClick={() => removeObjective(obj.id)}>✕</button>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginBottom: 8, fontWeight: 600, fontSize: 12, color: '#aaa' }}>Rewards</div>
        <div style={s.row}>
          <select style={{ ...s.select, width: 100 }} value={rewardType} onChange={e => setRewardType(e.target.value)}>
            <option value="gold">Gold</option>
            <option value="xp">XP</option>
            <option value="item">Item</option>
            <option value="equipment">Equipment</option>
            <option value="reputation">Reputation</option>
            <option value="skill_point">Skill Point</option>
          </select>
          <input style={{ ...s.input, flex: 2 }} placeholder="Reward name" value={rewardName} onChange={e => setRewardName(e.target.value)} />
          <input style={{ ...s.input, width: 80 }} placeholder="Qty" type="number" min="1" value={rewardQty} onChange={e => setRewardQty(e.target.value)} />
          <select style={{ ...s.select, width: 110 }} value={rewardRarity} onChange={e => setRewardRarity(e.target.value)}>
            <option value="common">Common</option>
            <option value="uncommon">Uncommon</option>
            <option value="rare">Rare</option>
            <option value="epic">Epic</option>
            <option value="legendary">Legendary</option>
          </select>
          <button style={s.btnSecondary} onClick={addReward}>+ Add</button>
        </div>
        {tempRewards.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 10 }}>
            {tempRewards.map(rw => (
              <div key={rw.id} style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#1a1a2e', borderRadius: 4, padding: '6px 10px' }}>
                <span style={{ flex: 1, fontSize: 12, color: '#ccc' }}>
                  {rw.name} x{rw.quantity}
                </span>
                <span style={{ ...s.tag, background: '#333', color: '#aaa' }}>{rw.type}</span>
                <span style={{ ...s.tag, background: (REWARD_RARITY_COLORS[rw.rarity] || '#888') + '22', color: REWARD_RARITY_COLORS[rw.rarity] || '#888' }}>{rw.rarity}</span>
                <button style={s.btnDanger} onClick={() => removeReward(rw.id)}>✕</button>
              </div>
            ))}
          </div>
        )}

        <button style={s.btn} onClick={handleComposeQuest}>
          <i className="fa-solid fa-wand-magic-sparkles" style={{ marginRight: 6 }} />
          Compose Quest
        </button>
      </div>

      <div style={s.card}>
        <div style={s.cardTitle}>
          <i className="fa-solid fa-list-check" style={{ color: '#74b9ff' }} />
          Created Quests ({quests.length})
        </div>
        {quests.length === 0 ? (
          <div style={{ color: '#666', fontSize: 12 }}>No quests created yet.</div>
        ) : (
          <div style={s.grid}>
            {quests.map(quest => (
              <div key={quest.id} style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, border: '1px solid #333', borderLeft: `3px solid ${getQuestTypeColor(quest.quest_type)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{quest.title}</span>
                  <span style={{ ...s.badge, background: getQuestTypeColor(quest.quest_type) + '22', color: getQuestTypeColor(quest.quest_type) }}>
                    {QUEST_TYPE_LABELS[quest.quest_type]}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#666', marginBottom: 6 }}>
                  ID: {quest.id}
                </div>
                <div style={{ display: 'flex', gap: 12, marginBottom: 6 }}>
                  <span style={s.label}>
                    Difficulty: <span style={{ color: getDifficultyColor(quest.difficulty), fontWeight: 600 }}>{quest.difficulty}/10</span>
                  </span>
                  <span style={s.label}>
                    Objectives: <span style={{ color: '#ccc' }}>{quest.objectives.length}</span>
                  </span>
                  <span style={s.label}>
                    Rewards: <span style={{ color: '#ccc' }}>{quest.rewards.length}</span>
                  </span>
                </div>
                {quest.objectives.length > 0 && (
                  <div style={{ marginBottom: 6 }}>
                    {quest.objectives.map(obj => (
                      <div key={obj.id} style={{ fontSize: 11, color: '#aaa', paddingLeft: 8, borderLeft: '2px solid #444', marginBottom: 2 }}>
                        {obj.description} (x{obj.required_count})
                        {obj.is_optional && <span style={{ ...s.tag, marginLeft: 4, background: '#fdcb6e22', color: '#fdcb6e' }}>Opt</span>}
                      </div>
                    ))}
                  </div>
                )}
                {quest.rewards.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {quest.rewards.map(rw => (
                      <span key={rw.id} style={{ ...s.tag, background: (REWARD_RARITY_COLORS[rw.rarity] || '#888') + '22', color: REWARD_RARITY_COLORS[rw.rarity] || '#888' }}>
                        {rw.name} x{rw.quantity}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderQuestChainsTab = () => (
    <div>
      <div style={s.card}>
        <div style={s.cardTitle}>
          <i className="fa-solid fa-link" style={{ color: '#a29bfe' }} />
          Compose Quest Chain
        </div>
        <div style={s.row}>
          <input style={{ ...s.input, flex: 2 }} placeholder="Chain Name" value={chainName} onChange={e => setChainName(e.target.value)} />
          <input style={{ ...s.input, flex: 2 }} placeholder="Narrative Theme" value={chainTheme} onChange={e => setChainTheme(e.target.value)} />
          <input style={{ ...s.input, width: 100 }} placeholder="Quests" type="number" min="2" max="20" value={chainQuestCount} onChange={e => setChainQuestCount(e.target.value)} />
        </div>
        <div style={s.row}>
          <span style={{ fontSize: 12, color: '#888' }}>Narrative Arc:</span>
          <select style={s.select} value={chainNarrativeArc} onChange={e => setChainNarrativeArc(e.target.value as NarrativeArc)}>
            {(Object.keys(NARRATIVE_ARC_LABELS) as NarrativeArc[]).map(a => (
              <option key={a} value={a}>{NARRATIVE_ARC_LABELS[a]}</option>
            ))}
          </select>
          <button style={s.btn} onClick={handleComposeChain}>
            <i className="fa-solid fa-wand-magic-sparkles" style={{ marginRight: 6 }} />
            Compose Chain
          </button>
        </div>
      </div>

      <div style={s.card}>
        <div style={s.cardTitle}>
          <i className="fa-solid fa-diagram-project" style={{ color: '#a29bfe' }} />
          Quest Chains ({chains.length})
        </div>
        {chains.length === 0 ? (
          <div style={{ color: '#666', fontSize: 12 }}>No chains created yet.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {chains.map(chain => (
              <div key={chain.id} style={{ background: '#1a1a2e', borderRadius: 8, padding: 14, border: '1px solid #333' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 14, color: '#ccc' }}>{chain.name}</span>
                    <span style={{ ...s.badge, marginLeft: 8, background: '#a29bfe22', color: '#a29bfe' }}>
                      {NARRATIVE_ARC_LABELS[chain.narrative_arc]}
                    </span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>ID: {chain.id}</span>
                </div>
                <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>
                  <i className="fa-solid fa-palette" style={{ marginRight: 4, color: '#fdcb6e' }} />
                  Theme: {chain.theme}
                </div>
                <div style={{ fontSize: 12, color: '#888', marginBottom: 10 }}>
                  Total Quests: <span style={{ color: '#e94560', fontWeight: 600 }}>{chain.total_quests}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 0, overflow: 'auto', padding: '8px 0' }}>
                  {Array.from({ length: chain.total_quests }).map((_, i) => (
                    <React.Fragment key={i}>
                      <div style={{
                        minWidth: 80, padding: '8px 10px', background: '#16213e', borderRadius: 6,
                        border: '1px solid #333', textAlign: 'center', fontSize: 11, color: '#aaa',
                      }}>
                        <div style={{ fontSize: 10, color: '#666' }}>Q{i + 1}</div>
                        <div style={{ color: '#ccc' }}>
                          {chain.quests?.find(q => q.order === i + 1)?.quest_title || `Quest ${i + 1}`}
                        </div>
                      </div>
                      {i < chain.total_quests - 1 && (
                        <div style={{ minWidth: 24, height: 2, background: '#444', margin: '0 4px' }} />
                      )}
                    </React.Fragment>
                  ))}
                </div>

                {chain.quests && chain.quests.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {chain.quests.map(node => (
                      <div key={node.quest_id} style={s.chainNode}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>
                            #{node.order} {node.quest_title}
                          </span>
                          <span style={{ fontSize: 10, color: '#666' }}>{node.quest_id}</span>
                        </div>
                        {node.prerequisites.length > 0 && (
                          <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
                            Prerequisites: {node.prerequisites.join(', ')}
                          </div>
                        )}
                        {node.unlocks.length > 0 && (
                          <div style={{ fontSize: 10, color: '#888' }}>
                            Unlocks: {node.unlocks.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderBranchingTab = () => (
    <div>
      <div style={s.card}>
        <div style={s.cardTitle}>
          <i className="fa-solid fa-code-branch" style={{ color: '#fdcb6e' }} />
          Add Branching Point
        </div>
        <div style={s.row}>
          <select style={{ ...s.select, flex: 2 }} value={branchQuestId} onChange={e => setBranchQuestId(e.target.value)}>
            <option value="">Select a quest...</option>
            {quests.map(q => (
              <option key={q.id} value={q.id}>{q.title} ({q.id})</option>
            ))}
          </select>
          <select style={s.select} value={branchConditionType} onChange={e => setBranchConditionType(e.target.value as BranchCondition)}>
            {(Object.keys(BRANCH_CONDITION_LABELS) as BranchCondition[]).map(c => (
              <option key={c} value={c}>{BRANCH_CONDITION_LABELS[c]}</option>
            ))}
          </select>
        </div>
        <div style={s.row}>
          <input style={{ ...s.input, flex: 2 }} placeholder={`Condition value (e.g. ">= 10" for level)`} value={branchConditionValue} onChange={e => setBranchConditionValue(e.target.value)} />
          <input style={{ ...s.input, flex: 2 }} placeholder="Narrative label" value={branchNarrativeLabel} onChange={e => setBranchNarrativeLabel(e.target.value)} />
        </div>
        <div style={s.row}>
          <input style={{ ...s.input, flex: 1 }} placeholder="True branch: Quest ID" value={branchTrueQuestId} onChange={e => setBranchTrueQuestId(e.target.value)} />
          <input style={{ ...s.input, flex: 1 }} placeholder="False branch: Quest ID" value={branchFalseQuestId} onChange={e => setBranchFalseQuestId(e.target.value)} />
        </div>
        <button style={s.btn} onClick={handleAddBranching}>
          <i className="fa-solid fa-plus" style={{ marginRight: 6 }} />
          Add Branching Point
        </button>
      </div>

      <div style={s.card}>
        <div style={s.cardTitle}>
          <i className="fa-solid fa-diagram-successor" style={{ color: '#fdcb6e' }} />
          Branching Points ({branches.length})
        </div>
        {branches.length === 0 ? (
          <div style={{ color: '#666', fontSize: 12 }}>No branching points added yet.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {branches.map(branch => (
              <div key={branch.id} style={{ background: '#1a1a2e', borderRadius: 8, padding: 14, border: '1px solid #333', borderLeft: '3px solid #fdcb6e' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>
                    {branch.quest_title}
                  </span>
                  <span style={{ ...s.badge, background: '#fdcb6e22', color: '#fdcb6e' }}>
                    {BRANCH_CONDITION_LABELS[branch.branch_config.condition_type]}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                  <div style={{ flex: 1, textAlign: 'center' }}>
                    <div style={{ fontSize: 10, color: '#666', marginBottom: 2 }}>Condition</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#fdcb6e' }}>
                      {branch.branch_config.condition_type} {branch.branch_config.condition_value}
                    </div>
                    {branch.branch_config.narrative_label && (
                      <div style={{ fontSize: 10, color: '#aaa', fontStyle: 'italic' }}>
                        &ldquo;{branch.branch_config.narrative_label}&rdquo;
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 12 }}>
                  <div style={{ flex: 1, background: '#16213e', borderRadius: 6, padding: 10, textAlign: 'center', border: '1px solid #333' }}>
                    <div style={{ fontSize: 10, color: '#6bcb77', marginBottom: 4 }}>✓ IF TRUE</div>
                    <div style={{ fontSize: 11, color: '#ccc' }}>
                      {branch.branch_config.true_quest_id || <span style={{ color: '#666' }}>Continue</span>}
                    </div>
                  </div>
                  <div style={{ flex: 1, background: '#16213e', borderRadius: 6, padding: 10, textAlign: 'center', border: '1px solid #333' }}>
                    <div style={{ fontSize: 10, color: '#ff6b6b', marginBottom: 4 }}>✗ IF FALSE</div>
                    <div style={{ fontSize: 11, color: '#ccc' }}>
                      {branch.branch_config.false_quest_id || <span style={{ color: '#666' }}>Alternate Path</span>}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderRewardsTab = () => (
    <div>
      <div style={s.card}>
        <div style={s.cardTitle}>
          <i className="fa-solid fa-coins" style={{ color: '#fdcb6e' }} />
          Compute Reward Balance
        </div>
        <div style={s.row}>
          <select style={{ ...s.select, flex: 2 }} value={rewardChainId} onChange={e => setRewardChainId(e.target.value)}>
            <option value="">Select a chain...</option>
            {chains.map(c => (
              <option key={c.id} value={c.id}>{c.name} ({c.id})</option>
            ))}
          </select>
          <button style={s.btn} onClick={handleComputeRewards}>
            <i className="fa-solid fa-calculator" style={{ marginRight: 6 }} />
            Compute Balance
          </button>
        </div>
      </div>

      {rewardBalanceResult && (
        <div style={s.card}>
          <div style={s.cardTitle}>
            <i className="fa-solid fa-chart-pie" style={{ color: '#6bcb77' }} />
            Reward Distribution: {rewardBalanceResult.chain_name}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 14 }}>
            <div style={{ background: '#1a1a2e', borderRadius: 6, padding: 10, textAlign: 'center', border: '1px solid #333' }}>
              <div style={{ fontSize: 10, color: '#666' }}>Total XP</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#6bcb77' }}>{rewardBalanceResult.total_xp.toLocaleString()}</div>
            </div>
            <div style={{ background: '#1a1a2e', borderRadius: 6, padding: 10, textAlign: 'center', border: '1px solid #333' }}>
              <div style={{ fontSize: 10, color: '#666' }}>Total Gold</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>{rewardBalanceResult.total_gold.toLocaleString()}</div>
            </div>
            <div style={{ background: '#1a1a2e', borderRadius: 6, padding: 10, textAlign: 'center', border: '1px solid #333' }}>
              <div style={{ fontSize: 10, color: '#666' }}>Total Items</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#74b9ff' }}>{rewardBalanceResult.total_items}</div>
            </div>
            <div style={{ background: '#1a1a2e', borderRadius: 6, padding: 10, textAlign: 'center', border: '1px solid #333' }}>
              <div style={{ fontSize: 10, color: '#666' }}>Balance Score</div>
              <div style={{
                fontSize: 16, fontWeight: 700,
                color: (rewardBalanceResult.balance_score ?? 0) >= 0.8 ? '#6bcb77' : (rewardBalanceResult.balance_score ?? 0) >= 0.5 ? '#fdcb6e' : '#ff6b6b',
              }}>
                {((rewardBalanceResult.balance_score ?? 0) * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>Per-Quest Breakdown</div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 4 }}>
              <span style={{ flex: 2, fontSize: 10, color: '#666' }}>XP</span>
              <span style={{ flex: 2, fontSize: 10, color: '#666' }}>Gold</span>
              <span style={{ flex: 1, fontSize: 10, color: '#666' }}>Items</span>
            </div>
            {(rewardBalanceResult.distribution.length > 0 ? rewardBalanceResult.distribution : [
              { quest_id: 'q1', quest_title: 'Quest 1', xp: rewardBalanceResult.xp_per_quest, gold: rewardBalanceResult.gold_per_quest, items: Math.ceil(rewardBalanceResult.total_items / 3) },
              { quest_id: 'q2', quest_title: 'Quest 2', xp: rewardBalanceResult.xp_per_quest, gold: rewardBalanceResult.gold_per_quest, items: Math.ceil(rewardBalanceResult.total_items / 3) },
              { quest_id: 'q3', quest_title: 'Quest 3', xp: rewardBalanceResult.xp_per_quest, gold: rewardBalanceResult.gold_per_quest, items: Math.ceil(rewardBalanceResult.total_items / 3) },
            ]).map((d, i) => {
              const maxVal = Math.max(rewardBalanceResult.xp_per_quest || 1, rewardBalanceResult.gold_per_quest || 1);
              return (
                <div key={d.quest_id || i} style={{ background: '#1a1a2e', borderRadius: 6, padding: '8px 10px', marginBottom: 6, border: '1px solid #333' }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#ccc', marginBottom: 6 }}>{d.quest_title}</div>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <div style={{ flex: 2 }}>
                      <div style={s.rewardBar}>
                        <div style={{ ...s.rewardBarFill, width: `${((d.xp / maxVal) * 100)}%`, background: '#6bcb77' }} />
                      </div>
                      <div style={{ fontSize: 10, color: '#6bcb77', marginTop: 2 }}>{d.xp} XP</div>
                    </div>
                    <div style={{ flex: 2 }}>
                      <div style={s.rewardBar}>
                        <div style={{ ...s.rewardBarFill, width: `${((d.gold / maxVal) * 100)}%`, background: '#fdcb6e' }} />
                      </div>
                      <div style={{ fontSize: 10, color: '#fdcb6e', marginTop: 2 }}>{d.gold} Gold</div>
                    </div>
                    <div style={{ flex: 1, textAlign: 'center' }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: '#74b9ff' }}>{d.items}</span>
                      <div style={{ fontSize: 10, color: '#666' }}>items</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {rewardBalanceResult.recommendations.length > 0 && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 6 }}>
                <i className="fa-solid fa-lightbulb" style={{ marginRight: 6, color: '#fdcb6e' }} />
                Recommendations
              </div>
              {rewardBalanceResult.recommendations.map((rec, i) => (
                <div key={i} style={{ fontSize: 11, color: '#aaa', padding: '6px 10px', background: '#1a1a2e', borderRadius: 4, marginBottom: 4, borderLeft: '2px solid #fdcb6e' }}>
                  {rec}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!rewardBalanceResult && (
        <div style={{ ...s.card, textAlign: 'center', color: '#666', fontSize: 12 }}>
          Select a quest chain above and click &ldquo;Compute Balance&rdquo; to see reward distribution.
        </div>
      )}
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'create-quest': return renderCreateQuestTab();
      case 'quest-chains': return renderQuestChainsTab();
      case 'branching': return renderBranchingTab();
      case 'rewards': return renderRewardsTab();
      default: return null;
    }
  };

  const tabs: { id: TabId; label: string; icon: string }[] = [
    { id: 'create-quest', label: 'Create Quest', icon: 'fa-scroll' },
    { id: 'quest-chains', label: 'Quest Chains', icon: 'fa-link' },
    { id: 'branching', label: 'Branching', icon: 'fa-code-branch' },
    { id: 'rewards', label: 'Rewards', icon: 'fa-coins' },
  ];

  return (
    <div style={s.container}>
      <div style={s.header}>
        <div style={s.title}>
          <i className="fa-solid fa-book" style={{ color: '#e94560' }} />
          Quest Composer
        </div>
        <div style={{ fontSize: 10, color: '#666' }}>
          AI-Driven Quest Composition
        </div>
      </div>

      <div style={s.tabs}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            style={{ ...s.tab, ...(activeTab === tab.id ? s.tabActive : {}) }}
            onClick={() => setActiveTab(tab.id)}
          >
            <i className={`fa-solid ${tab.icon}`} style={{ marginRight: 6 }} />
            {tab.label}
          </button>
        ))}
      </div>

      <div style={s.body}>
        {message && (
          <div style={
            message.type === 'success' ? s.msgSuccess :
            message.type === 'error' ? s.msgError :
            s.msgInfo
          }>
            {message.text}
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#888' }}>
            <i className="fa-solid fa-spinner fa-spin" style={{ fontSize: 20, marginBottom: 10, display: 'block' }} />
            Loading...
          </div>
        ) : (
          <>
            {renderStats()}
            {renderTabContent()}
          </>
        )}
      </div>
    </div>
  );
};

export default QuestComposerPanel;