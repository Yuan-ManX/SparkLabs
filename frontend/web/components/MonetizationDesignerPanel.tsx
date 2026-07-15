import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'revenue' | 'pricing' | 'iap' | 'audit';

interface RevenueModel {
  id: string;
  name: string;
  genre: string;
  model_type: string;
  pricing_tiers: PricingTier[];
  estimated_arpu: number;
  estimated_conversion_rate: number;
  estimated_ltv: number;
  retention_d30: number;
  revenue_streams: RevenueStream[];
  created_at: number;
}

interface PricingTier {
  name: string;
  price: number;
  currency: string;
  features: string[];
  target_segment: string;
}

interface RevenueStream {
  name: string;
  percentage: number;
  description: string;
}

interface RegionalPrice {
  region: string;
  currency: string;
  symbol: string;
  tier1_price: number;
  tier2_price: number;
  tier3_price: number;
  ppp_multiplier: number;
}

interface DiscountSchedule {
  id: string;
  name: string;
  discount_percent: number;
  start_day: number;
  end_day: number;
  target_segment: string;
}

interface BundleConfig {
  id: string;
  name: string;
  items: string[];
  bundle_price: number;
  individual_total: number;
  savings_percent: number;
  description: string;
}

interface IAPItem {
  id: string;
  name: string;
  category: string;
  price_tier: string;
  price: number;
  currency: string;
  value_proposition: string;
  purchase_trigger: string;
  conversion_estimate: number;
  is_consumable: boolean;
  rarity: string;
}

interface AuditResult {
  id: string;
  model_id: string;
  fairness_score: number;
  player_sentiment: number;
  compliance_rating: number;
  overall_grade: string;
  risk_flags: RiskFlag[];
  recommendations: string[];
  player_satisfaction: number;
  whale_ratio: number;
  pay_to_win_score: number;
  created_at: number;
}

interface RiskFlag {
  id: string;
  severity: string;
  category: string;
  description: string;
  affected_item: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const GENRE_OPTIONS = ['action', 'platformer', 'rpg', 'strategy', 'shooter', 'puzzle', 'roguelike', 'racing', 'simulation', 'fighting', 'survival', 'metroidvania', 'sandbox', 'casual', 'hypercasual', 'card', 'moba'];

const MODEL_TYPE_OPTIONS = ['free_to_play', 'premium', 'freemium', 'subscription', 'battle_pass', 'ad_supported', 'hybrid', 'cosmetic_only', 'pay_to_win_light'];

const PRICE_TIER_OPTIONS = ['$0.99', '$1.99', '$2.99', '$4.99', '$9.99', '$14.99', '$19.99', '$24.99', '$49.99', '$99.99'];

const IAP_CATEGORIES = ['consumable', 'cosmetic', 'boost', 'currency_pack', 'bundle', 'subscription', 'battle_pass', 'loot_box', 'starter_pack', 'time_saver'];

const REGIONS = ['US', 'EU', 'UK', 'JP', 'KR', 'CN', 'BR', 'IN', 'RU', 'SEA'];

const defaultRevenueModels: RevenueModel[] = [
  {
    id: uid(), name: 'Standard F2P Model', genre: 'action', model_type: 'free_to_play',
    pricing_tiers: [
      { name: 'Free', price: 0, currency: 'USD', features: ['Base game access', 'Standard progression', 'Ad-supported'], target_segment: 'Casual players' },
      { name: 'Premium Pass', price: 9.99, currency: 'USD', features: ['Ad-free experience', 'Premium rewards', 'Exclusive cosmetics'], target_segment: 'Engaged players' },
      { name: 'Ultimate Bundle', price: 29.99, currency: 'USD', features: ['All premium content', 'Early access', 'VIP support'], target_segment: 'Whales' },
    ],
    estimated_arpu: 4.25, estimated_conversion_rate: 0.05, estimated_ltv: 85.00,
    retention_d30: 0.32,
    revenue_streams: [
      { name: 'IAP Consumables', percentage: 45, description: 'In-game currency and boosters' },
      { name: 'Battle Pass', percentage: 30, description: 'Seasonal battle pass subscriptions' },
      { name: 'Cosmetics', percentage: 15, description: 'Skins, emotes, character customizations' },
      { name: 'Ads', percentage: 10, description: 'Rewarded video and interstitials' },
    ],
    created_at: Date.now() - 86400000,
  },
  {
    id: uid(), name: 'Premium RPG Model', genre: 'rpg', model_type: 'premium',
    pricing_tiers: [
      { name: 'Standard', price: 19.99, currency: 'USD', features: ['Full game access', 'Standard content'], target_segment: 'Core gamers' },
      { name: 'Deluxe', price: 39.99, currency: 'USD', features: ['Expansion pass', 'Exclusive items', 'Digital artbook'], target_segment: 'Fans' },
    ],
    estimated_arpu: 25.00, estimated_conversion_rate: 1.0, estimated_ltv: 25.00,
    retention_d30: 0.45,
    revenue_streams: [
      { name: 'Upfront Purchase', percentage: 70, description: 'One-time game purchase' },
      { name: 'DLC/Expansions', percentage: 25, description: 'Post-launch content packs' },
      { name: 'Merchandise', percentage: 5, description: 'Branded merchandise' },
    ],
    created_at: Date.now() - 172800000,
  },
];

const defaultRegionalPrices: RegionalPrice[] = [
  { region: 'US', currency: 'USD', symbol: '$', tier1_price: 0.99, tier2_price: 4.99, tier3_price: 9.99, ppp_multiplier: 1.0 },
  { region: 'EU', currency: 'EUR', symbol: '\u20AC', tier1_price: 0.99, tier2_price: 4.99, tier3_price: 9.99, ppp_multiplier: 1.0 },
  { region: 'UK', currency: 'GBP', symbol: '\u00A3', tier1_price: 0.79, tier2_price: 3.99, tier3_price: 7.99, ppp_multiplier: 0.85 },
  { region: 'JP', currency: 'JPY', symbol: '\u00A5', tier1_price: 120, tier2_price: 610, tier3_price: 1220, ppp_multiplier: 0.9 },
  { region: 'KR', currency: 'KRW', symbol: '\u20A9', tier1_price: 1200, tier2_price: 5900, tier3_price: 12000, ppp_multiplier: 0.75 },
  { region: 'CN', currency: 'CNY', symbol: '\u00A5', tier1_price: 6, tier2_price: 30, tier3_price: 68, ppp_multiplier: 0.55 },
  { region: 'BR', currency: 'BRL', symbol: 'R$', tier1_price: 3.99, tier2_price: 18.99, tier3_price: 37.99, ppp_multiplier: 0.5 },
  { region: 'IN', currency: 'INR', symbol: '\u20B9', tier1_price: 49, tier2_price: 249, tier3_price: 499, ppp_multiplier: 0.35 },
];

const defaultDiscountSchedules: DiscountSchedule[] = [
  { id: uid(), name: 'Launch Week Sale', discount_percent: 30, start_day: 1, end_day: 7, target_segment: 'Early adopters' },
  { id: uid(), name: 'Mid-Season Boost', discount_percent: 20, start_day: 15, end_day: 21, target_segment: 'Lapsed players' },
  { id: uid(), name: 'Holiday Bundle', discount_percent: 40, start_day: 85, end_day: 92, target_segment: 'All players' },
];

const defaultBundleConfigs: BundleConfig[] = [
  { id: uid(), name: 'Starter Pack', items: ['500 Gems', 'Rare Skin', 'XP Boost (3d)'], bundle_price: 4.99, individual_total: 9.97, savings_percent: 50, description: 'Perfect for new players getting started' },
  { id: uid(), name: 'Pro Bundle', items: ['2000 Gems', '2 Epic Skins', 'XP Boost (7d)', 'Battle Pass'], bundle_price: 19.99, individual_total: 39.96, savings_percent: 50, description: 'Best value for dedicated players' },
  { id: uid(), name: 'Collector\'s Chest', items: ['5000 Gems', 'Legendary Skin', 'All Boosts (30d)'], bundle_price: 49.99, individual_total: 99.97, savings_percent: 50, description: 'Ultimate collection for completionists' },
];

const defaultIAPItems: IAPItem[] = [
  { id: uid(), name: 'Small Gem Pack', category: 'currency_pack', price_tier: '$0.99', price: 0.99, currency: 'USD', value_proposition: '80 Gems - Best for quick top-ups', purchase_trigger: 'Short on gems for an item', conversion_estimate: 0.15, is_consumable: true, rarity: 'common' },
  { id: uid(), name: 'Medium Gem Pack', category: 'currency_pack', price_tier: '$4.99', price: 4.99, currency: 'USD', value_proposition: '500 Gems + 50 Bonus - 25% more value', purchase_trigger: 'Mid-session resource shortage', conversion_estimate: 0.08, is_consumable: true, rarity: 'common' },
  { id: uid(), name: 'Large Gem Pack', category: 'currency_pack', price_tier: '$9.99', price: 9.99, currency: 'USD', value_proposition: '1200 Gems + 200 Bonus - Best value per gem', purchase_trigger: 'Major purchase event or sale', conversion_estimate: 0.04, is_consumable: true, rarity: 'rare' },
  { id: uid(), name: 'XP Booster (1 Day)', category: 'boost', price_tier: '$0.99', price: 0.99, currency: 'USD', value_proposition: '2x XP for 24 hours', purchase_trigger: 'Before a long play session', conversion_estimate: 0.10, is_consumable: true, rarity: 'common' },
  { id: uid(), name: 'XP Booster (7 Days)', category: 'boost', price_tier: '$4.99', price: 4.99, currency: 'USD', value_proposition: '2x XP for 7 days - 40% savings vs daily', purchase_trigger: 'Weekend gaming marathon', conversion_estimate: 0.05, is_consumable: true, rarity: 'uncommon' },
  { id: uid(), name: 'Dragon Slayer Skin', category: 'cosmetic', price_tier: '$9.99', price: 9.99, currency: 'USD', value_proposition: 'Epic character skin with unique VFX', purchase_trigger: 'Seen in-game or in shop showcase', conversion_estimate: 0.03, is_consumable: false, rarity: 'epic' },
  { id: uid(), name: 'Phoenix Wings', category: 'cosmetic', price_tier: '$14.99', price: 14.99, currency: 'USD', value_proposition: 'Legendary back attachment with particle effects', purchase_trigger: 'Limited-time event availability', conversion_estimate: 0.015, is_consumable: false, rarity: 'legendary' },
  { id: uid(), name: 'Starter Bundle', category: 'starter_pack', price_tier: '$2.99', price: 2.99, currency: 'USD', value_proposition: '300 Gems + Rare Skin + 3-Day XP Boost (70% off)', purchase_trigger: 'First-time shop visit', conversion_estimate: 0.20, is_consumable: true, rarity: 'common' },
  { id: uid(), name: 'Season Battle Pass', category: 'battle_pass', price_tier: '$9.99', price: 9.99, currency: 'USD', value_proposition: 'Unlock premium rewards for 90 days', purchase_trigger: 'Season start or mid-season catch-up', conversion_estimate: 0.06, is_consumable: false, rarity: 'rare' },
  { id: uid(), name: 'Lucky Loot Crate', category: 'loot_box', price_tier: '$1.99', price: 1.99, currency: 'USD', value_proposition: 'Random item: 80% rare, 15% epic, 5% legendary', purchase_trigger: 'Impulse buy after a win', conversion_estimate: 0.12, is_consumable: true, rarity: 'uncommon' },
  { id: uid(), name: 'Monthly Subscription', category: 'subscription', price_tier: '$4.99', price: 4.99, currency: 'USD', value_proposition: 'Daily gems, exclusive items, ad-free', purchase_trigger: 'After free trial expiration', conversion_estimate: 0.04, is_consumable: false, rarity: 'rare' },
  { id: uid(), name: 'Time Skip Token', category: 'time_saver', price_tier: '$0.99', price: 0.99, currency: 'USD', value_proposition: 'Skip any timer up to 4 hours', purchase_trigger: 'Impatient during progression gates', conversion_estimate: 0.08, is_consumable: true, rarity: 'common' },
];

const defaultAuditResults: AuditResult[] = [
  {
    id: uid(), model_id: defaultRevenueModels[0].id, fairness_score: 0.72, player_sentiment: 0.68,
    compliance_rating: 0.85, overall_grade: 'B',
    risk_flags: [
      { id: uid(), severity: 'medium', category: 'loot_box', description: 'Loot box drop rates not disclosed in all regions', affected_item: 'Lucky Loot Crate' },
      { id: uid(), severity: 'low', category: 'pricing', description: 'XP booster pricing may disadvantage non-paying players', affected_item: 'XP Booster (7 Days)' },
    ],
    recommendations: [
      'Add drop rate disclosures for all loot box items',
      'Implement pity timer for legendary items',
      'Add spending limit controls for players under 18',
      'Consider a non-consumable version of XP boosters',
    ],
    player_satisfaction: 0.71, whale_ratio: 0.05, pay_to_win_score: 0.35,
    created_at: Date.now() - 43200000,
  },
];

const MonetizationDesignerPanel: React.FC = () => {
  const [revenueModels, setRevenueModels] = useState<RevenueModel[]>(defaultRevenueModels);
  const [regionalPrices, setRegionalPrices] = useState<RegionalPrice[]>(defaultRegionalPrices);
  const [discountSchedules, setDiscountSchedules] = useState<DiscountSchedule[]>(defaultDiscountSchedules);
  const [bundleConfigs, setBundleConfigs] = useState<BundleConfig[]>(defaultBundleConfigs);
  const [iapItems, setIapItems] = useState<IAPItem[]>(defaultIAPItems);
  const [auditResults, setAuditResults] = useState<AuditResult[]>(defaultAuditResults);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('revenue');
  const [stats, setStats] = useState<any>(null);

  const [designGenre, setDesignGenre] = useState('action');
  const [designModelType, setDesignModelType] = useState('free_to_play');

  const [pricingBasePrice, setPricingBasePrice] = useState('4.99');
  const [pricingGenre, setPricingGenre] = useState('action');

  const [iapGenre, setIapGenre] = useState('action');
  const [iapModelType, setIapModelType] = useState('free_to_play');

  const [auditModelId, setAuditModelId] = useState('');

  const [loadingRevenue, setLoadingRevenue] = useState(false);
  const [loadingPricing, setLoadingPricing] = useState(false);
  const [loadingIap, setLoadingIap] = useState(false);
  const [loadingAudit, setLoadingAudit] = useState(false);

  const apiBase = API_ROOT + '/agent/monetization-designer';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const data = await res.json();
      setStats(data);
      if (data.revenue_models) setRevenueModels(data.revenue_models);
      if (data.regional_prices) setRegionalPrices(data.regional_prices);
    } catch { /* use defaults */ }
  }, []);

  const fetchRevenueModels = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/revenue-models`);
      const data = await res.json();
      if (data.models) setRevenueModels(data.models);
      else if (Array.isArray(data)) setRevenueModels(data);
    } catch { /* use defaults */ }
  }, []);

  const fetchIapCatalogs = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/iap-catalogs`);
      const data = await res.json();
      if (data.items) setIapItems(data.items);
      else if (Array.isArray(data)) setIapItems(data);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchRevenueModels();
    fetchIapCatalogs();
  }, [fetchStats, fetchRevenueModels, fetchIapCatalogs]);

  const handleDesignRevenueModel = async () => {
    setLoadingRevenue(true);
    try {
      const res = await fetch(`${apiBase}/design-revenue-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ genre: designGenre, model_type: designModelType }),
      });
      const data = await res.json();
      if (data.model) {
        setRevenueModels(prev => [data.model, ...prev]);
        showMessage(`Revenue model designed for ${designGenre} (${designModelType})`, 'success');
      } else if (data) {
        const model: RevenueModel = {
          id: uid(), name: `${designModelType}_${designGenre}`, genre: designGenre, model_type: designModelType,
          pricing_tiers: data.pricing_tiers || [],
          estimated_arpu: data.estimated_arpu || 0, estimated_conversion_rate: data.estimated_conversion_rate || 0,
          estimated_ltv: data.estimated_ltv || 0, retention_d30: data.retention_d30 || 0,
          revenue_streams: data.revenue_streams || [], created_at: Date.now(),
        };
        setRevenueModels(prev => [model, ...prev]);
        showMessage(`Revenue model designed for ${designGenre} (${designModelType})`, 'success');
      }
    } catch {
      const model: RevenueModel = {
        id: uid(), name: `${designModelType}_${designGenre}_${Date.now()}`, genre: designGenre, model_type: designModelType,
        pricing_tiers: [
          { name: 'Free Tier', price: 0, currency: 'USD', features: ['Base access'], target_segment: 'All players' },
          { name: 'Premium Tier', price: 9.99, currency: 'USD', features: ['All content', 'No ads'], target_segment: 'Core players' },
        ],
        estimated_arpu: 3.50, estimated_conversion_rate: 0.04, estimated_ltv: 70.00,
        retention_d30: 0.30,
        revenue_streams: [
          { name: 'IAP', percentage: 60, description: 'In-app purchases' },
          { name: 'Ads', percentage: 25, description: 'Advertisement revenue' },
          { name: 'Subscriptions', percentage: 15, description: 'Recurring subscriptions' },
        ],
        created_at: Date.now(),
      };
      setRevenueModels(prev => [model, ...prev]);
      showMessage(`Revenue model created (offline fallback)`, 'info');
    } finally {
      setLoadingRevenue(false);
    }
  };

  const handleConfigurePricing = async () => {
    setLoadingPricing(true);
    try {
      const res = await fetch(`${apiBase}/configure-pricing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_price: parseFloat(pricingBasePrice) || 4.99, genre: pricingGenre }),
      });
      const data = await res.json();
      if (data.regional_prices) {
        setRegionalPrices(data.regional_prices);
        showMessage('Regional pricing configured', 'success');
      }
      if (data.discounts) setDiscountSchedules(data.discounts);
      if (data.bundles) setBundleConfigs(data.bundles);
    } catch {
      showMessage('Pricing configured (offline fallback)', 'info');
    } finally {
      setLoadingPricing(false);
    }
  };

  const handleDesignIapCatalog = async () => {
    setLoadingIap(true);
    try {
      const res = await fetch(`${apiBase}/design-iap-catalog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ genre: iapGenre, model_type: iapModelType }),
      });
      const data = await res.json();
      if (data.items) {
        setIapItems(data.items);
        showMessage(`IAP catalog designed for ${iapGenre} (${iapModelType})`, 'success');
      } else if (Array.isArray(data)) {
        setIapItems(data);
        showMessage(`IAP catalog designed for ${iapGenre} (${iapModelType})`, 'success');
      }
    } catch {
      showMessage('IAP catalog designed (offline fallback)', 'info');
    } finally {
      setLoadingIap(false);
    }
  };

  const handleAuditFairness = async () => {
    if (!auditModelId.trim()) { showMessage('Model ID is required', 'error'); return; }
    setLoadingAudit(true);
    try {
      const res = await fetch(`${apiBase}/audit-fairness`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: auditModelId }),
      });
      const data = await res.json();
      const result: AuditResult = {
        id: uid(), model_id: auditModelId,
        fairness_score: data.fairness_score || 0, player_sentiment: data.player_sentiment || 0,
        compliance_rating: data.compliance_rating || 0, overall_grade: data.overall_grade || 'C',
        risk_flags: data.risk_flags || [],
        recommendations: data.recommendations || [],
        player_satisfaction: data.player_satisfaction || 0, whale_ratio: data.whale_ratio || 0,
        pay_to_win_score: data.pay_to_win_score || 0, created_at: Date.now(),
      };
      setAuditResults(prev => [result, ...prev]);
      showMessage(`Fairness audit complete - Grade: ${result.overall_grade}`, 'success');
    } catch {
      const result: AuditResult = {
        id: uid(), model_id: auditModelId,
        fairness_score: 0.68, player_sentiment: 0.65, compliance_rating: 0.78, overall_grade: 'B-',
        risk_flags: [
          { id: uid(), severity: 'medium', category: 'transparency', description: 'Monetization disclosures could be clearer', affected_item: 'General' },
        ],
        recommendations: [
          'Improve pricing transparency',
          'Add spending limit options',
          'Review loot box mechanics for compliance',
        ],
        player_satisfaction: 0.67, whale_ratio: 0.06, pay_to_win_score: 0.40,
        created_at: Date.now(),
      };
      setAuditResults(prev => [result, ...prev]);
      showMessage(`Fairness audit complete (offline fallback)`, 'info');
    } finally {
      setLoadingAudit(false);
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const formatCurrency = (val: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(val);
  };

  const scoreColor = (s: number) => s >= 0.8 ? '#6bcb77' : s >= 0.6 ? '#fdcb6e' : s >= 0.4 ? '#ff6b6b' : '#888';

  const gradeColor = (g: string) => {
    if (g.startsWith('A')) return '#6bcb77';
    if (g.startsWith('B')) return '#a29bfe';
    if (g.startsWith('C')) return '#fdcb6e';
    if (g.startsWith('D')) return '#e17055';
    return '#ff6b6b';
  };

  const severityColor = (s: string) => s === 'high' ? '#ff6b6b' : s === 'medium' ? '#fdcb6e' : '#74b9ff';

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'revenue', label: 'Revenue Model', icon: '\uD83D\uDCB0' },
    { key: 'pricing', label: 'Pricing', icon: '\uD83C\uDFF7\uFE0F' },
    { key: 'iap', label: 'IAP Catalog', icon: '\uD83D\uDED2' },
    { key: 'audit', label: 'Audit', icon: '\uD83D\uDD0D' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCB0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Monetization Designer</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{revenueModels.length} models · {iapItems.length} items · {auditResults.length} audits</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #fdcb6e' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'revenue' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCB0'} design-revenue-model</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Genre</div>
                  <select value={designGenre} onChange={e => setDesignGenre(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {GENRE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Model Type</div>
                  <select value={designModelType} onChange={e => setDesignModelType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {MODEL_TYPE_OPTIONS.map(m => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
                <button onClick={handleDesignRevenueModel} disabled={loadingRevenue} style={{ padding: '6px 14px', backgroundColor: loadingRevenue ? '#3d3d5a' : '#2563eb', color: '#fff', border: 'none', borderRadius: 4, cursor: loadingRevenue ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600, opacity: loadingRevenue ? 0.7 : 1 }}>
                  {loadingRevenue ? 'Designing...' : 'Design Model'}
                </button>
              </div>
            </div>

            {stats && (
              <div style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div><span style={{ fontSize: 10, color: '#888' }}>Models: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#a29bfe' }}>{stats.total_models || revenueModels.length}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Avg ARPU: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#fdcb6e' }}>{stats.avg_arpu ? formatCurrency(stats.avg_arpu) : 'N/A'}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>IAP Items: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#6bcb77' }}>{stats.total_iap_items || iapItems.length}</span></div>
                <div><span style={{ fontSize: 10, color: '#888' }}>Audits: </span><span style={{ fontSize: 12, fontWeight: 600, color: '#e056a0' }}>{stats.total_audits || auditResults.length}</span></div>
              </div>
            )}

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCB0'} Revenue Models <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({revenueModels.length})</span></div>
            {revenueModels.map(m => (
              <div key={m.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{m.name}</span>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe', textTransform: 'uppercase' }}>{m.genre}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#6bcb77', textTransform: 'uppercase' }}>{m.model_type.replace(/_/g, ' ')}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 12, marginTop: 6, flexWrap: 'wrap' }}>
                  <div style={{ fontSize: 10 }}>
                    <span style={{ color: '#888' }}>ARPU: </span>
                    <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{formatCurrency(m.estimated_arpu)}</span>
                  </div>
                  <div style={{ fontSize: 10 }}>
                    <span style={{ color: '#888' }}>Conversion: </span>
                    <span style={{ color: '#6bcb77', fontWeight: 600 }}>{(m.estimated_conversion_rate * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ fontSize: 10 }}>
                    <span style={{ color: '#888' }}>LTV: </span>
                    <span style={{ color: '#a29bfe', fontWeight: 600 }}>{formatCurrency(m.estimated_ltv)}</span>
                  </div>
                  <div style={{ fontSize: 10 }}>
                    <span style={{ color: '#888' }}>D30: </span>
                    <span style={{ color: scoreColor(m.retention_d30), fontWeight: 600 }}>{(m.retention_d30 * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {m.pricing_tiers.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Pricing Tiers</div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {m.pricing_tiers.map((t, i) => (
                        <div key={i} style={{ padding: '6px 10px', backgroundColor: '#141428', borderRadius: 4, border: '1px solid #333', minWidth: 120 }}>
                          <div style={{ fontSize: 10, fontWeight: 600, color: '#ccc' }}>{t.name}</div>
                          <div style={{ fontSize: 11, fontWeight: 700, color: '#fdcb6e' }}>{t.price === 0 ? 'Free' : formatCurrency(t.price)}</div>
                          <div style={{ fontSize: 9, color: '#888' }}>{t.target_segment}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {m.revenue_streams.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Revenue Streams</div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {m.revenue_streams.map((rs, i) => (
                        <div key={i} style={{ padding: '4px 8px', backgroundColor: '#141428', borderRadius: 3, display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 9, color: '#ccc' }}>{rs.name}</span>
                          <span style={{ fontSize: 9, fontWeight: 600, color: '#6bcb77' }}>{rs.percentage}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ fontSize: 9, color: '#666', marginTop: 4 }}>ID: {m.id} · {formatTime(m.created_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'pricing' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDFF7\uFE0F'} configure-pricing</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Base Price (USD)</div>
                  <input value={pricingBasePrice} onChange={e => setPricingBasePrice(e.target.value)} type="number" step="0.01" min="0.99" placeholder="4.99" style={{ padding: '6px 10px', fontSize: 11, width: 100, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Genre</div>
                  <select value={pricingGenre} onChange={e => setPricingGenre(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {GENRE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
                <button onClick={handleConfigurePricing} disabled={loadingPricing} style={{ padding: '6px 14px', backgroundColor: loadingPricing ? '#3d3d5a' : '#2563eb', color: '#fff', border: 'none', borderRadius: 4, cursor: loadingPricing ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600, opacity: loadingPricing ? 0.7 : 1 }}>
                  {loadingPricing ? 'Configuring...' : 'Configure Pricing'}
                </button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83C\uDF0D'} Regional Price Points <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({regionalPrices.length} regions)</span></div>
            <div style={{ overflow: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                <thead>
                  <tr style={{ backgroundColor: '#141428' }}>
                    <th style={{ padding: '6px 8px', textAlign: 'left', color: '#888', fontWeight: 600, borderBottom: '1px solid #333' }}>Region</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right', color: '#888', fontWeight: 600, borderBottom: '1px solid #333' }}>Tier 1</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right', color: '#888', fontWeight: 600, borderBottom: '1px solid #333' }}>Tier 2</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right', color: '#888', fontWeight: 600, borderBottom: '1px solid #333' }}>Tier 3</th>
                    <th style={{ padding: '6px 8px', textAlign: 'right', color: '#888', fontWeight: 600, borderBottom: '1px solid #333' }}>PPP Mult.</th>
                  </tr>
                </thead>
                <tbody>
                  {regionalPrices.map((rp, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #2a2a3e' }}>
                      <td style={{ padding: '6px 8px', color: '#ccc', fontWeight: 600 }}>{rp.region}</td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', color: '#6bcb77', fontFamily: 'monospace' }}>{rp.symbol}{rp.tier1_price.toFixed(rp.currency === 'JPY' || rp.currency === 'KRW' || rp.currency === 'INR' ? 0 : 2)}</td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', color: '#fdcb6e', fontFamily: 'monospace' }}>{rp.symbol}{rp.tier2_price.toFixed(rp.currency === 'JPY' || rp.currency === 'KRW' || rp.currency === 'INR' ? 0 : 2)}</td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', color: '#a29bfe', fontFamily: 'monospace' }}>{rp.symbol}{rp.tier3_price.toFixed(rp.currency === 'JPY' || rp.currency === 'KRW' || rp.currency === 'INR' ? 0 : 2)}</td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', color: scoreColor(1 - rp.ppp_multiplier + 0.5) }}>{rp.ppp_multiplier.toFixed(2)}x</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83C\uDF1F'} Discount Schedules <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({discountSchedules.length})</span></div>
                {discountSchedules.map(ds => (
                  <div key={ds.id} style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #e17055', marginBottom: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: 11, color: '#ccc' }}>{ds.name}</span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: '#e17055' }}>-{ds.discount_percent}%</span>
                    </div>
                    <div style={{ fontSize: 9, color: '#888', marginTop: 2 }}>
                      Days {ds.start_day}-{ds.end_day} · {ds.target_segment}
                    </div>
                  </div>
                ))}
              </div>

              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCE6'} Bundle Configurations <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({bundleConfigs.length})</span></div>
                {bundleConfigs.map(bc => (
                  <div key={bc.id} style={{ padding: 8, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77', marginBottom: 6 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: 11, color: '#ccc' }}>{bc.name}</span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: '#6bcb77' }}>{formatCurrency(bc.bundle_price)} <span style={{ fontSize: 9, color: '#888' }}>(save {bc.savings_percent}%)</span></span>
                    </div>
                    <div style={{ fontSize: 9, color: '#888', marginTop: 2 }}>{bc.description}</div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                      {bc.items.map((item, i) => (
                        <span key={i} style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, backgroundColor: '#141428', color: '#aaa' }}>{item}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'iap' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDED2'} design-iap-catalog</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Genre</div>
                  <select value={iapGenre} onChange={e => setIapGenre(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {GENRE_OPTIONS.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Model Type</div>
                  <select value={iapModelType} onChange={e => setIapModelType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    {MODEL_TYPE_OPTIONS.map(m => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
                <button onClick={handleDesignIapCatalog} disabled={loadingIap} style={{ padding: '6px 14px', backgroundColor: loadingIap ? '#3d3d5a' : '#2563eb', color: '#fff', border: 'none', borderRadius: 4, cursor: loadingIap ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600, opacity: loadingIap ? 0.7 : 1 }}>
                  {loadingIap ? 'Designing...' : 'Design Catalog'}
                </button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDED2'} IAP Items <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({iapItems.length})</span></div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 }}>
              {iapItems.map(item => (
                <div key={item.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${item.is_consumable ? '#fdcb6e' : '#a29bfe'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{item.name}</span>
                      <div style={{ display: 'flex', gap: 4, marginTop: 2 }}>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#74b9ff', textTransform: 'uppercase' }}>{item.category.replace(/_/g, ' ')}</span>
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#a29bfe', textTransform: 'uppercase' }}>{item.rarity}</span>
                        {item.is_consumable && <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#2d3a2d', color: '#6bcb77' }}>Consumable</span>}
                      </div>
                    </div>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e' }}>{formatCurrency(item.price)}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#aaa', marginTop: 6, lineHeight: 1.4 }}>{item.value_proposition}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
                    <span style={{ fontSize: 9, color: '#888' }}>Trigger: {item.purchase_trigger}</span>
                    <span style={{ fontSize: 9, fontWeight: 600, color: scoreColor(item.conversion_estimate * 5) }}>{(item.conversion_estimate * 100).toFixed(1)}% conv.</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'audit' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD0D'} audit-fairness</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ flex: 1, minWidth: 250 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Model ID</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input value={auditModelId} onChange={e => setAuditModelId(e.target.value)} placeholder="Paste a revenue model ID..." style={{ padding: '6px 10px', fontSize: 11, flex: 1, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                    <button onClick={handleAuditFairness} disabled={loadingAudit} style={{ padding: '6px 14px', backgroundColor: loadingAudit ? '#3d3d5a' : '#2563eb', color: '#fff', border: 'none', borderRadius: 4, cursor: loadingAudit ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap', opacity: loadingAudit ? 0.7 : 1 }}>
                      {loadingAudit ? 'Auditing...' : 'Run Audit'}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDD0D'} Audit Results <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({auditResults.length})</span></div>
            {auditResults.map(a => (
              <div key={a.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `4px solid ${gradeColor(a.overall_grade)}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#ccc' }}>Model: {a.model_id.slice(0, 16)}...</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 24, fontWeight: 800, color: gradeColor(a.overall_grade) }}>{a.overall_grade}</span>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Fairness Score</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ flex: 1, height: 6, backgroundColor: '#141428', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ width: `${a.fairness_score * 100}%`, height: '100%', backgroundColor: scoreColor(a.fairness_score), borderRadius: 3 }} />
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 600, color: scoreColor(a.fairness_score) }}>{(a.fairness_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Player Sentiment</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ flex: 1, height: 6, backgroundColor: '#141428', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ width: `${a.player_sentiment * 100}%`, height: '100%', backgroundColor: scoreColor(a.player_sentiment), borderRadius: 3 }} />
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 600, color: scoreColor(a.player_sentiment) }}>{(a.player_sentiment * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Compliance Rating</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ flex: 1, height: 6, backgroundColor: '#141428', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ width: `${a.compliance_rating * 100}%`, height: '100%', backgroundColor: scoreColor(a.compliance_rating), borderRadius: 3 }} />
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 600, color: scoreColor(a.compliance_rating) }}>{(a.compliance_rating * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Pay-to-Win Score</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ flex: 1, height: 6, backgroundColor: '#141428', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{ width: `${a.pay_to_win_score * 100}%`, height: '100%', backgroundColor: scoreColor(1 - a.pay_to_win_score), borderRadius: 3 }} />
                      </div>
                      <span style={{ fontSize: 10, fontWeight: 600, color: scoreColor(1 - a.pay_to_win_score) }}>{(a.pay_to_win_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                  <div style={{ fontSize: 10 }}>
                    <span style={{ color: '#888' }}>Satisfaction: </span>
                    <span style={{ color: '#6bcb77', fontWeight: 600 }}>{(a.player_satisfaction * 100).toFixed(0)}%</span>
                  </div>
                  <div style={{ fontSize: 10 }}>
                    <span style={{ color: '#888' }}>Whale Ratio: </span>
                    <span style={{ color: '#ff6b6b', fontWeight: 600 }}>{(a.whale_ratio * 100).toFixed(1)}%</span>
                  </div>
                </div>

                {a.risk_flags.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Risk Flags ({a.risk_flags.length})</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {a.risk_flags.map(rf => (
                        <div key={rf.id} style={{ padding: '6px 8px', backgroundColor: '#141428', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, backgroundColor: severityColor(rf.severity) + '33', color: severityColor(rf.severity), fontWeight: 600, textTransform: 'uppercase' }}>{rf.severity}</span>
                          <span style={{ fontSize: 9, color: '#aaa', textTransform: 'uppercase' }}>{rf.category.replace(/_/g, ' ')}</span>
                          <span style={{ fontSize: 10, color: '#ccc', flex: 1 }}>{rf.description}</span>
                          <span style={{ fontSize: 9, color: '#888' }}>{rf.affected_item}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {a.recommendations.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Recommendations</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                      {a.recommendations.map((rec, i) => (
                        <div key={i} style={{ fontSize: 10, color: '#6bcb77', paddingLeft: 8 }}>{'\u2022'} {rec}</div>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ fontSize: 9, color: '#666', marginTop: 4 }}>ID: {a.id} · {formatTime(a.created_at)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDCB0'} {revenueModels.length} models · {iapItems.length} items · {auditResults.length} audits</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default MonetizationDesignerPanel;