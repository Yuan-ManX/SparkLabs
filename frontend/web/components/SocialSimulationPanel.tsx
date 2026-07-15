import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'characters' | 'relationships' | 'network' | 'events';
type Faction = 'order_of_light' | 'shadow_syndicate' | 'free_markets' | 'arcane_academy' | 'wild_tribes' | 'neutral';

interface Character {
  id: string;
  name: string;
  faction: Faction;
  backstory: string;
  social_goals: string;
  extroversion: number;
  agreeableness: number;
  loyalty: number;
  charisma: number;
  created_at: string;
}

interface Relationship {
  id: string;
  npc_a_id: string;
  npc_a_name: string;
  npc_b_id: string;
  npc_b_name: string;
  relationship_type: string;
  strength: number;
  trust: number;
  tension: number;
  description: string;
}

interface NetworkStats {
  total_characters: number;
  total_relationships: number;
  network_density: number;
  average_trust: number;
  average_tension: number;
  faction_count: number;
  conflict_hotspots: string[];
  most_influential: string;
  most_connected: string;
  factions: { name: string; member_count: number; influence: number }[];
}

interface SocialEvent {
  id: string;
  event_type: string;
  participants: string[];
  impact_score: number;
  ripple_effects: string[];
  description: string;
  created_at: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const FACTION_LABELS: Record<Faction, string> = {
  order_of_light: 'Order of Light',
  shadow_syndicate: 'Shadow Syndicate',
  free_markets: 'Free Markets',
  arcane_academy: 'Arcane Academy',
  wild_tribes: 'Wild Tribes',
  neutral: 'Neutral',
};

const FACTION_COLORS: Record<Faction, string> = {
  order_of_light: '#fdcb6e',
  shadow_syndicate: '#a29bfe',
  free_markets: '#6bcb77',
  arcane_academy: '#74b9ff',
  wild_tribes: '#e17055',
  neutral: '#888',
};

const RELATIONSHIP_TYPES = ['ally', 'rival', 'neutral', 'mentor', 'dependent', 'family', 'romantic', 'hostile'];

const EVENT_TYPES = ['alliance_formed', 'betrayal', 'trade_deal', 'conflict', 'festival', 'discovery', 'power_shift', 'migration'];

const SocialSimulationPanel: React.FC = () => {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [networkStats, setNetworkStats] = useState<NetworkStats | null>(null);
  const [events, setEvents] = useState<SocialEvent[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('characters');

  const [charName, setCharName] = useState('');
  const [charFaction, setCharFaction] = useState<Faction>('neutral');
  const [charBackstory, setCharBackstory] = useState('');
  const [charGoals, setCharGoals] = useState('');

  const [relNpcA, setRelNpcA] = useState('');
  const [relNpcB, setRelNpcB] = useState('');
  const [loadingRel, setLoadingRel] = useState(false);
  const [loadingNetwork, setLoadingNetwork] = useState(false);
  const [loadingEvent, setLoadingEvent] = useState(false);
  const [loadingChar, setLoadingChar] = useState(false);

  const apiBase = API_ROOT + '/agent/social-simulation';

  const defaultCharacters: Character[] = [
    { id: uid(), name: 'Lady Elara', faction: 'order_of_light', backstory: 'A noble knight seeking justice across the realm', social_goals: 'Unite the fractured kingdoms', extroversion: 0.75, agreeableness: 0.85, loyalty: 0.9, charisma: 0.8, created_at: '3 days ago' },
    { id: uid(), name: 'Vex Darkwater', faction: 'shadow_syndicate', backstory: 'A cunning smuggler who rose through underworld ranks', social_goals: 'Control the black market trade routes', extroversion: 0.6, agreeableness: 0.2, loyalty: 0.3, charisma: 0.75, created_at: '1 week ago' },
    { id: uid(), name: 'Trader Jin', faction: 'free_markets', backstory: 'A traveling merchant with connections everywhere', social_goals: 'Establish a continental trade network', extroversion: 0.85, agreeableness: 0.7, loyalty: 0.5, charisma: 0.9, created_at: '2 weeks ago' },
    { id: uid(), name: 'Archmage Thalia', faction: 'arcane_academy', backstory: 'A brilliant scholar obsessed with forbidden knowledge', social_goals: 'Unlock the secrets of ancient magic', extroversion: 0.3, agreeableness: 0.5, loyalty: 0.7, charisma: 0.55, created_at: '5 days ago' },
    { id: uid(), name: 'Gorn Bloodfang', faction: 'wild_tribes', backstory: 'A fierce warrior chieftain of the northern clans', social_goals: 'Protect ancestral lands from invaders', extroversion: 0.5, agreeableness: 0.3, loyalty: 0.95, charisma: 0.65, created_at: '4 days ago' },
  ];

  const defaultRelationships: Relationship[] = [
    { id: uid(), npc_a_id: 'char-1', npc_a_name: 'Lady Elara', npc_b_id: 'char-2', npc_b_name: 'Vex Darkwater', relationship_type: 'rival', strength: 0.7, trust: 0.15, tension: 0.85, description: 'Ideological opposites locked in a cold war' },
    { id: uid(), npc_a_id: 'char-1', npc_a_name: 'Lady Elara', npc_b_id: 'char-3', npc_b_name: 'Trader Jin', relationship_type: 'ally', strength: 0.65, trust: 0.7, tension: 0.2, description: 'Mutual benefit: protection for trade access' },
    { id: uid(), npc_a_id: 'char-2', npc_a_name: 'Vex Darkwater', npc_b_id: 'char-3', npc_b_name: 'Trader Jin', relationship_type: 'neutral', strength: 0.4, trust: 0.3, tension: 0.5, description: 'Cautious business dealings only' },
  ];

  const defaultNetwork: NetworkStats = {
    total_characters: 5,
    total_relationships: 3,
    network_density: 0.3,
    average_trust: 0.38,
    average_tension: 0.52,
    faction_count: 5,
    conflict_hotspots: ['Lady Elara vs Vex Darkwater', 'Shadow Syndicate territory dispute'],
    most_influential: 'Lady Elara',
    most_connected: 'Trader Jin',
    factions: [
      { name: 'Order of Light', member_count: 1, influence: 0.85 },
      { name: 'Shadow Syndicate', member_count: 1, influence: 0.7 },
      { name: 'Free Markets', member_count: 1, influence: 0.6 },
      { name: 'Arcane Academy', member_count: 1, influence: 0.75 },
      { name: 'Wild Tribes', member_count: 1, influence: 0.55 },
    ],
  };

  const defaultEvents: SocialEvent[] = [
    { id: uid(), event_type: 'alliance_formed', participants: ['Lady Elara', 'Trader Jin'], impact_score: 0.72, ripple_effects: ['Trade routes secured', 'Shadow Syndicate loses market access'], description: 'Lady Elara and Trader Jin formalize a trade-protection pact', created_at: '2 hours ago' },
    { id: uid(), event_type: 'conflict', participants: ['Vex Darkwater', 'Lady Elara'], impact_score: 0.88, ripple_effects: ['Increased patrols', 'Rising tension in border towns'], description: 'A skirmish at the border between Order and Syndicate forces', created_at: '6 hours ago' },
    { id: uid(), event_type: 'discovery', participants: ['Archmage Thalia'], impact_score: 0.55, ripple_effects: ['Academic interest surges', 'Rival scholars seek collaboration'], description: 'Archmage Thalia discovers an ancient text in the academy vaults', created_at: '1 day ago' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      setNetworkStats(data);
    } catch {
      setNetworkStats(defaultNetwork);
    }
  }, []);

  const fetchCharacters = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/characters`);
      const data = await res.json();
      if (data.characters && data.characters.length > 0) setCharacters(data.characters);
    } catch {
      // use defaults
    }
  }, []);

  const fetchRelationships = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/relationships`);
      const data = await res.json();
      if (data.relationships && data.relationships.length > 0) setRelationships(data.relationships);
    } catch {
      // use defaults
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/events`);
      const data = await res.json();
      if (data.events && data.events.length > 0) setEvents(data.events);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setCharacters(defaultCharacters);
    setRelationships(defaultRelationships);
    setEvents(defaultEvents);
    fetchStats();
    fetchCharacters();
    fetchRelationships();
    fetchEvents();
  }, [fetchStats, fetchCharacters, fetchRelationships, fetchEvents]);

  const handleCreateCharacter = async () => {
    const name = charName.trim() || `Character ${characters.length + 1}`;
    setLoadingChar(true);
    try {
      await fetch(`${apiBase}/create-character`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, faction: charFaction, backstory: charBackstory, social_goals: charGoals }),
      });
      showMessage(`Character "${name}" created`, 'success');
      fetchCharacters();
      fetchStats();
    } catch {
      const traits = {
        extroversion: Math.round((0.3 + Math.random() * 0.7) * 100) / 100,
        agreeableness: Math.round((0.3 + Math.random() * 0.7) * 100) / 100,
        loyalty: Math.round((0.3 + Math.random() * 0.7) * 100) / 100,
        charisma: Math.round((0.3 + Math.random() * 0.7) * 100) / 100,
      };
      const character: Character = {
        id: uid(),
        name,
        faction: charFaction,
        backstory: charBackstory || 'A mysterious figure with unknown origins',
        social_goals: charGoals || 'Forge their own path in the world',
        ...traits,
        created_at: 'just now',
      };
      setCharacters(prev => [character, ...prev]);
      setCharName(''); setCharBackstory(''); setCharGoals('');
      showMessage(`Character "${name}" created (offline fallback)`, 'info');
    } finally {
      setLoadingChar(false);
    }
  };

  const handleSimulateRelationship = async () => {
    if (!relNpcA.trim() || !relNpcB.trim()) {
      showMessage('Please select both characters', 'error');
      return;
    }
    if (relNpcA === relNpcB) {
      showMessage('Cannot create a relationship with the same character', 'error');
      return;
    }
    setLoadingRel(true);
    try {
      const res = await fetch(`${apiBase}/simulate-relationship`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ npc_a_id: relNpcA, npc_b_id: relNpcB }),
      });
      const data = await res.json();
      const rel: Relationship = {
        id: data.id || uid(),
        npc_a_id: relNpcA,
        npc_a_name: data.npc_a_name || characters.find(c => c.id === relNpcA)?.name || relNpcA,
        npc_b_id: relNpcB,
        npc_b_name: data.npc_b_name || characters.find(c => c.id === relNpcB)?.name || relNpcB,
        relationship_type: data.relationship_type || RELATIONSHIP_TYPES[Math.floor(Math.random() * RELATIONSHIP_TYPES.length)],
        strength: data.strength ?? Math.round((0.3 + Math.random() * 0.7) * 100) / 100,
        trust: data.trust ?? Math.round(Math.random() * 100) / 100,
        tension: data.tension ?? Math.round(Math.random() * 100) / 100,
        description: data.description || 'A newly formed relationship',
      };
      setRelationships(prev => [rel, ...prev]);
      showMessage('Relationship simulated', 'success');
      fetchStats();
    } catch {
      const npcA = characters.find(c => c.id === relNpcA) || { name: relNpcA };
      const npcB = characters.find(c => c.id === relNpcB) || { name: relNpcB };
      const rel: Relationship = {
        id: uid(),
        npc_a_id: relNpcA,
        npc_a_name: npcA.name,
        npc_b_id: relNpcB,
        npc_b_name: npcB.name,
        relationship_type: RELATIONSHIP_TYPES[Math.floor(Math.random() * RELATIONSHIP_TYPES.length)],
        strength: Math.round((0.3 + Math.random() * 0.7) * 100) / 100,
        trust: Math.round(Math.random() * 100) / 100,
        tension: Math.round(Math.random() * 100) / 100,
        description: 'A newly formed relationship',
      };
      setRelationships(prev => [rel, ...prev]);
      showMessage('Relationship simulated (offline fallback)', 'info');
    } finally {
      setLoadingRel(false);
    }
  };

  const handleBuildNetwork = async () => {
    setLoadingNetwork(true);
    try {
      const res = await fetch(`${apiBase}/build-network`, { method: 'POST' });
      const data = await res.json();
      setNetworkStats(data);
      showMessage('Social network built successfully', 'success');
      fetchRelationships();
    } catch {
      setNetworkStats(defaultNetwork);
      showMessage('Social network built (offline fallback)', 'info');
    } finally {
      setLoadingNetwork(false);
    }
  };

  const handleGenerateEvent = async () => {
    setLoadingEvent(true);
    try {
      const res = await fetch(`${apiBase}/generate-event`, { method: 'POST' });
      const data = await res.json();
      const evt: SocialEvent = {
        id: data.id || uid(),
        event_type: data.event_type || EVENT_TYPES[Math.floor(Math.random() * EVENT_TYPES.length)],
        participants: data.participants || [characters[0]?.name || 'Unknown', characters[1]?.name || 'Unknown'],
        impact_score: data.impact_score ?? Math.round(Math.random() * 100) / 100,
        ripple_effects: data.ripple_effects || ['Faction relations shift', 'New opportunities arise'],
        description: data.description || 'A social event unfolds in the network',
        created_at: 'just now',
      };
      setEvents(prev => [evt, ...prev]);
      showMessage('Social event generated', 'success');
      fetchStats();
    } catch {
      const evt: SocialEvent = {
        id: uid(),
        event_type: EVENT_TYPES[Math.floor(Math.random() * EVENT_TYPES.length)],
        participants: characters.length >= 2
          ? [characters[Math.floor(Math.random() * characters.length)].name, characters[Math.floor(Math.random() * characters.length)].name]
          : ['Unknown'],
        impact_score: Math.round(Math.random() * 100) / 100,
        ripple_effects: ['Faction relations shift', 'New opportunities arise'],
        description: 'A social event unfolds in the network',
        created_at: 'just now',
      };
      setEvents(prev => [evt, ...prev]);
      showMessage('Social event generated (offline fallback)', 'info');
    } finally {
      setLoadingEvent(false);
    }
  };

  const getTraitColor = (value: number): string => {
    if (value >= 0.7) return '#6bcb77';
    if (value >= 0.4) return '#fdcb6e';
    return '#ff6b6b';
  };

  const getTraitBg = (value: number): string => {
    if (value >= 0.7) return '#1a3a1a';
    if (value >= 0.4) return '#3a3a1a';
    return '#3a1a1a';
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'characters', label: 'Characters', icon: '\uD83D\uDC64', count: characters.length },
    { key: 'relationships', label: 'Relationships', icon: '\uD83D\uDD17', count: relationships.length },
    { key: 'network', label: 'Social Network', icon: '\uD83C\uDF10', count: networkStats?.total_relationships || 0 },
    { key: 'events', label: 'Events', icon: '\u26A1', count: events.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF0D'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Social Simulation</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {networkStats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {networkStats.total_characters} chars · {networkStats.total_relationships} rels
            </span>
          )}
        </div>
      </div>

      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'characters' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\u2795'} Create Character
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Name</div>
                  <input
                    value={charName}
                    onChange={e => setCharName(e.target.value)}
                    placeholder="Character name..."
                    style={{
                      padding: '6px 10px', fontSize: 11, width: 140,
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}
                  />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Faction</div>
                  <select
                    value={charFaction}
                    onChange={e => setCharFaction(e.target.value as Faction)}
                    style={{
                      padding: '6px 10px', fontSize: 11,
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}>
                    {Object.entries(FACTION_LABELS).map(([key, label]) => (
                      <option key={key} value={key}>{label}</option>
                    ))}
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Backstory</div>
                  <input
                    value={charBackstory}
                    onChange={e => setCharBackstory(e.target.value)}
                    placeholder="Brief backstory..."
                    style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}
                  />
                </div>
                <div style={{ flex: 1, minWidth: 180 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Social Goals</div>
                  <input
                    value={charGoals}
                    onChange={e => setCharGoals(e.target.value)}
                    placeholder="What do they want socially?"
                    style={{
                      padding: '6px 10px', fontSize: 11, width: '100%',
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}
                  />
                </div>
                <button
                  onClick={handleCreateCharacter}
                  disabled={loadingChar}
                  style={{
                    padding: '6px 14px', backgroundColor: loadingChar ? '#1a2a3a' : '#2d3a5a',
                    color: loadingChar ? '#666' : '#74b9ff',
                    border: '1px solid #3d4a6a', borderRadius: 4,
                    cursor: loadingChar ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600,
                  }}>
                  {loadingChar ? 'Creating...' : '\u2795 Create'}
                </button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDC64'} Characters <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({characters.length})</span>
            </div>

            {characters.map(char => (
              <div key={char.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${FACTION_COLORS[char.faction]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{char.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: FACTION_COLORS[char.faction] + '33',
                      color: FACTION_COLORS[char.faction], fontWeight: 600,
                    }}>
                      {FACTION_LABELS[char.faction]}
                    </span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{char.created_at}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>
                  {char.backstory}
                </div>
                <div style={{ fontSize: 10, color: '#666', marginBottom: 8 }}>
                  Goals: <span style={{ color: '#aaa' }}>{char.social_goals}</span>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {(['extroversion', 'agreeableness', 'loyalty', 'charisma'] as const).map(trait => (
                    <div key={trait} style={{
                      display: 'flex', flexDirection: 'column', gap: 2,
                      flex: 1, minWidth: 80,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9 }}>
                        <span style={{ color: '#888', textTransform: 'capitalize' }}>{trait}</span>
                        <span style={{ color: getTraitColor(char[trait]) }}>{(char[trait] * 100).toFixed(0)}%</span>
                      </div>
                      <div style={{ height: 3, backgroundColor: '#141428', borderRadius: 2 }}>
                        <div style={{
                          height: '100%', width: `${char[trait] * 100}%`,
                          backgroundColor: getTraitColor(char[trait]), borderRadius: 2,
                        }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {characters.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDC64'}</span>
                No characters created yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'relationships' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD17'} Simulate Relationship
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Character A</div>
                  <select
                    value={relNpcA}
                    onChange={e => setRelNpcA(e.target.value)}
                    style={{
                      padding: '6px 10px', fontSize: 11, width: 170,
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}>
                    <option value="">Select character...</option>
                    {characters.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Character B</div>
                  <select
                    value={relNpcB}
                    onChange={e => setRelNpcB(e.target.value)}
                    style={{
                      padding: '6px 10px', fontSize: 11, width: 170,
                      backgroundColor: '#141428', color: '#ccc',
                      border: '1px solid #333', borderRadius: 4, outline: 'none',
                    }}>
                    <option value="">Select character...</option>
                    {characters.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleSimulateRelationship}
                  disabled={loadingRel}
                  style={{
                    padding: '6px 14px',
                    backgroundColor: loadingRel ? '#1a2a3a' : '#3a2d4a',
                    color: loadingRel ? '#666' : '#a29bfe',
                    border: '1px solid #4a3d5a', borderRadius: 4,
                    cursor: loadingRel ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600,
                  }}>
                  {loadingRel ? 'Simulating...' : '\uD83D\uDD17 Simulate'}
                </button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD17'} Relationships <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({relationships.length})</span>
            </div>

            {relationships.map(rel => (
              <div key={rel.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${
                  rel.relationship_type === 'ally' || rel.relationship_type === 'family' || rel.relationship_type === 'romantic' ? '#6bcb77' :
                  rel.relationship_type === 'rival' || rel.relationship_type === 'hostile' ? '#ff6b6b' :
                  rel.relationship_type === 'mentor' ? '#74b9ff' : '#fdcb6e'
                }`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{rel.npc_a_name}</span>
                    <span style={{ color: '#666', fontSize: 10 }}>{'\u2194'}</span>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{rel.npc_b_name}</span>
                  </div>
                  <span style={{
                    fontSize: 9, padding: '2px 8px', borderRadius: 3,
                    backgroundColor: rel.relationship_type === 'ally' ? '#1a3a1a' :
                      rel.relationship_type === 'hostile' ? '#3a1a1a' : '#1a2a3a',
                    color: rel.relationship_type === 'ally' ? '#6bcb77' :
                      rel.relationship_type === 'hostile' ? '#ff6b6b' : '#74b9ff',
                    fontWeight: 600, textTransform: 'uppercase',
                  }}>
                    {rel.relationship_type}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 8 }}>{rel.description}</div>
                <div style={{ display: 'flex', gap: 12 }}>
                  {(['strength', 'trust', 'tension'] as const).map(metric => {
                    const val = rel[metric];
                    return (
                      <div key={metric} style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, marginBottom: 2 }}>
                          <span style={{ color: '#888', textTransform: 'capitalize' }}>{metric}</span>
                          <span style={{ color: metric === 'tension' ? (val >= 0.7 ? '#ff6b6b' : val >= 0.4 ? '#fdcb6e' : '#6bcb77') : (val >= 0.7 ? '#6bcb77' : val >= 0.4 ? '#fdcb6e' : '#ff6b6b'), fontWeight: 600 }}>
                            {(val * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div style={{ height: 3, backgroundColor: '#141428', borderRadius: 2 }}>
                          <div style={{
                            height: '100%', width: `${val * 100}%`,
                            backgroundColor: metric === 'tension' ? '#e17055' : '#6bcb77',
                            borderRadius: 2,
                          }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

            {relationships.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD17'}</span>
                No relationships simulated yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'network' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleBuildNetwork}
                disabled={loadingNetwork}
                style={{
                  padding: '8px 16px',
                  backgroundColor: loadingNetwork ? '#1a2a3a' : 'bg-blue-600',
                  background: loadingNetwork ? '#1a2a3a' : '#2563eb',
                  color: loadingNetwork ? '#666' : '#fff',
                  border: 'none', borderRadius: 4,
                  cursor: loadingNetwork ? 'not-allowed' : 'pointer',
                  fontSize: 12, fontWeight: 600,
                }}>
                {loadingNetwork ? 'Building...' : '\uD83C\uDF10 Build Network'}
              </button>
              <button
                onClick={handleGenerateEvent}
                disabled={loadingEvent}
                style={{
                  padding: '8px 16px',
                  backgroundColor: loadingEvent ? '#1a2a3a' : '#1e1e1e',
                  background: loadingEvent ? '#1a2a3a' : '#2d3a4a',
                  color: loadingEvent ? '#666' : '#fdcb6e',
                  border: '1px solid #3d4a5a', borderRadius: 4,
                  cursor: loadingEvent ? 'not-allowed' : 'pointer',
                  fontSize: 12, fontWeight: 600,
                }}>
                {loadingEvent ? 'Generating...' : '\u26A1 Generate Event'}
              </button>
            </div>

            {networkStats && (
              <>
                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                    {'\uD83D\uDCCA'} Network Stats
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
                    <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                      <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Density</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#6bcb77' }}>
                        {(networkStats.network_density * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                      <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Avg Trust</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#74b9ff' }}>
                        {(networkStats.average_trust * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                      <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Avg Tension</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#ff6b6b' }}>
                        {(networkStats.average_tension * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                      <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Factions</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#fdcb6e' }}>
                        {networkStats.faction_count}
                      </div>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                      <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Characters</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#a29bfe' }}>
                        {networkStats.total_characters}
                      </div>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#141428', borderRadius: 4 }}>
                      <div style={{ fontSize: 9, color: '#666', textTransform: 'uppercase' }}>Relationships</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#e17055' }}>
                        {networkStats.total_relationships}
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                    {'\uD83C\uDFF0'} Faction Map
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {(networkStats.factions || []).map(f => (
                      <div key={f.name} style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        padding: 8, backgroundColor: '#141428', borderRadius: 4,
                      }}>
                        <span style={{ width: 120, fontSize: 11, fontWeight: 600, color: '#ccc' }}>{f.name}</span>
                        <span style={{ fontSize: 10, color: '#888', width: 80 }}>
                          {f.member_count} member{f.member_count !== 1 ? 's' : ''}
                        </span>
                        <div style={{ flex: 1, height: 6, backgroundColor: '#0d0d0d', borderRadius: 3 }}>
                          <div style={{
                            height: '100%', width: `${f.influence * 100}%`,
                            backgroundColor: f.influence >= 0.7 ? '#6bcb77' : f.influence >= 0.4 ? '#fdcb6e' : '#ff6b6b',
                            borderRadius: 3,
                          }} />
                        </div>
                        <span style={{ fontSize: 10, color: '#aaa', fontWeight: 600, width: 40, textAlign: 'right' }}>
                          {(f.influence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                    {'\uD83D\uDD25'} Conflict Hotspots
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {(networkStats.conflict_hotspots || []).map((hotspot, i) => (
                      <div key={i} style={{
                        padding: '6px 10px', backgroundColor: '#141428', borderRadius: 4,
                        fontSize: 10, color: '#ff6b6b', borderLeft: '3px solid #e17055',
                      }}>
                        {hotspot}
                      </div>
                    ))}
                    {(networkStats.conflict_hotspots || []).length === 0 && (
                      <div style={{ fontSize: 10, color: '#666', padding: '6px 10px' }}>No active conflicts</div>
                    )}
                  </div>
                </div>

                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e', display: 'flex', gap: 16,
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Most Influential</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#fdcb6e' }}>
                      {networkStats.most_influential || 'N/A'}
                    </div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Most Connected</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#74b9ff' }}>
                      {networkStats.most_connected || 'N/A'}
                    </div>
                  </div>
                </div>
              </>
            )}

            {!networkStats && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83C\uDF10'}</span>
                No network built yet. Click Build Network to start.
              </div>
            )}
          </div>
        )}

        {activeTab === 'events' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <button
                onClick={handleGenerateEvent}
                disabled={loadingEvent}
                style={{
                  padding: '8px 16px',
                  backgroundColor: loadingEvent ? '#1a2a3a' : '#1e1e1e',
                  background: loadingEvent ? '#1a2a3a' : '#2d3a4a',
                  color: loadingEvent ? '#666' : '#fdcb6e',
                  border: '1px solid #3d4a5a', borderRadius: 4,
                  cursor: loadingEvent ? 'not-allowed' : 'pointer',
                  fontSize: 12, fontWeight: 600,
                }}>
                {loadingEvent ? 'Generating...' : '\u26A1 Generate Event'}
              </button>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\u26A1'} Event History <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({events.length})</span>
            </div>

            {events.map(evt => (
              <div key={evt.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${
                  evt.event_type === 'alliance_formed' || evt.event_type === 'trade_deal' || evt.event_type === 'festival' ? '#6bcb77' :
                  evt.event_type === 'betrayal' || evt.event_type === 'conflict' ? '#ff6b6b' :
                  evt.event_type === 'discovery' ? '#74b9ff' :
                  evt.event_type === 'power_shift' ? '#fdcb6e' : '#a29bfe'
                }`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 3,
                      backgroundColor: evt.event_type === 'alliance_formed' || evt.event_type === 'trade_deal' ? '#1a3a1a' :
                        evt.event_type === 'betrayal' || evt.event_type === 'conflict' ? '#3a1a1a' : '#1a2a3a',
                      color: evt.event_type === 'alliance_formed' || evt.event_type === 'trade_deal' ? '#6bcb77' :
                        evt.event_type === 'betrayal' || evt.event_type === 'conflict' ? '#ff6b6b' : '#74b9ff',
                      fontWeight: 600, textTransform: 'uppercase',
                    }}>
                      {evt.event_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{evt.created_at}</span>
                </div>
                <div style={{ fontSize: 10, color: '#aaa', marginBottom: 6 }}>{evt.description}</div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>
                  Participants: {evt.participants.join(', ')}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 9, color: '#666' }}>Impact:</span>
                  <div style={{ flex: 1, height: 4, backgroundColor: '#141428', borderRadius: 2 }}>
                    <div style={{
                      height: '100%', width: `${evt.impact_score * 100}%`,
                      backgroundColor: evt.impact_score >= 0.7 ? '#ff6b6b' : evt.impact_score >= 0.4 ? '#fdcb6e' : '#6bcb77',
                      borderRadius: 2,
                    }} />
                  </div>
                  <span style={{ fontSize: 9, fontWeight: 600, color: evt.impact_score >= 0.7 ? '#ff6b6b' : evt.impact_score >= 0.4 ? '#fdcb6e' : '#6bcb77' }}>
                    {(evt.impact_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {(evt.ripple_effects || []).map((effect, i) => (
                    <span key={i} style={{
                      fontSize: 9, padding: '2px 6px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#a29bfe',
                    }}>
                      {'\u2192'} {effect}
                    </span>
                  ))}
                </div>
              </div>
            ))}

            {events.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\u26A1'}</span>
                No events generated yet
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83C\uDF0D'} {characters.length} chars · {relationships.length} rels · {events.length} events
        </span>
        <span>
          {networkStats ? `Density: ${(networkStats.network_density * 100).toFixed(0)}%` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default SocialSimulationPanel;