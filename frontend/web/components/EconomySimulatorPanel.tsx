import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

interface EconomyStats {
  gdp: number;
  gini_coefficient: number;
  inflation_rate: number;
  market_health: number;
  active_trades: number;
}

interface MarketItem {
  id: string;
  name: string;
  category: string;
  base_price: number;
  current_price: number;
  supply: number;
  demand: number;
  trend: 'up' | 'down' | 'stable';
}

interface Currency {
  code: string;
  name: string;
  exchange_rate: number;
  supply: number;
}

interface Imbalance {
  id: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  affected_market: string;
}

interface EconomySnapshot {
  gdp: number;
  gini: number;
  inflation: number;
  timestamp: string;
}

type TabId = 'overview' | 'market' | 'currencies' | 'imbalances';

export default function EconomySimulatorPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<EconomyStats | null>(null);
  const [marketItems, setMarketItems] = useState<MarketItem[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [imbalances, setImbalances] = useState<Imbalance[]>([]);
  const [snapshot, setSnapshot] = useState<EconomySnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  // Market form
  const [itemName, setItemName] = useState('');
  const [itemCategory, setItemCategory] = useState('commodity');
  const [itemBasePrice, setItemBasePrice] = useState('100');

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/economy-simulator/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchMarketItems = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/economy-simulator/market`);
      const data = await res.json();
      if (data.items) setMarketItems(data.items);
    } catch {}
  }, []);

  const fetchCurrencies = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/economy-simulator/currencies`);
      const data = await res.json();
      if (data.currencies) setCurrencies(data.currencies);
    } catch {}
  }, []);

  const fetchImbalances = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/economy-simulator/imbalances`);
      const data = await res.json();
      if (data.imbalances) setImbalances(data.imbalances);
    } catch {}
  }, []);

  const fetchSnapshot = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/economy-simulator/snapshot`);
      const data = await res.json();
      if (!data.error) setSnapshot(data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchMarketItems();
    fetchCurrencies();
    fetchImbalances();
    fetchSnapshot();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchMarketItems, fetchCurrencies, fetchImbalances, fetchSnapshot]);

  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), 3000);
  };

  const handleSimulateTick = async () => {
    try {
      const res = await fetch(`${API_BASE}/economy-simulator/tick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage('Economy tick simulated');
        fetchStats();
        fetchMarketItems();
        fetchImbalances();
        fetchSnapshot();
      }
    } catch {
      showMessage('Failed to simulate tick');
    }
  };

  const handleAddMarketItem = async () => {
    if (!itemName.trim()) { showMessage('Item name required'); return; }
    try {
      const res = await fetch(`${API_BASE}/economy-simulator/market`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: itemName,
          category: itemCategory,
          base_price: parseFloat(itemBasePrice),
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Market item "${itemName}" added`);
        setItemName('');
        fetchMarketItems();
      }
    } catch {
      showMessage('Failed to add market item');
    }
  };

  const TABS: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'market', label: 'Market' },
    { id: 'currencies', label: 'Currencies' },
    { id: 'imbalances', label: 'Imbalances' },
  ];

  const ITEM_CATEGORIES = ['commodity', 'weapon', 'armor', 'consumable', 'material', 'luxury', 'service'];

  const getTrendIcon = (trend: 'up' | 'down' | 'stable'): string => {
    switch (trend) {
      case 'up': return '▲';
      case 'down': return '▼';
      case 'stable': return '─';
    }
  };

  const getTrendColor = (trend: 'up' | 'down' | 'stable'): string => {
    switch (trend) {
      case 'up': return '#4ade80';
      case 'down': return '#f87171';
      case 'stable': return '#888';
    }
  };

  const getSeverityColor = (severity: string): string => {
    const colors: Record<string, string> = {
      critical: '#ef4444',
      high: '#f97316',
      medium: '#f59e0b',
      low: '#10b981',
    };
    return colors[severity] || '#888';
  };

  if (loading) {
    return (
      <div style={{ padding: 24, color: '#a0a0b0' }}>
        Loading Economy Simulator...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, color: '#e0e0e0' }}>
      <h2 style={{ margin: '0 0 8px 0', fontSize: 20, color: '#fff' }}>
        Economy Simulator
      </h2>
      <p style={{ margin: '0 0 16px 0', fontSize: 12, color: '#888' }}>
        Simulate in-game markets, currencies, and economic dynamics
      </p>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #333' }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 16px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid #f59e0b' : '2px solid transparent',
              color: activeTab === tab.id ? '#f59e0b' : '#888',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: activeTab === tab.id ? 600 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div style={{
          padding: '8px 12px',
          background: '#1a1a2e',
          border: '1px solid #f59e0b',
          borderRadius: 6,
          marginBottom: 12,
          fontSize: 12,
          color: '#fcd34d',
        }}>
          {message}
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div>
          {stats ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              <StatCard label="GDP" value={stats.gdp.toLocaleString()} accent="#f59e0b" />
              <StatCard label="Gini Coefficient" value={stats.gini_coefficient.toFixed(3)} accent="#f59e0b" />
              <StatCard label="Inflation Rate" value={`${(stats.inflation_rate * 100).toFixed(1)}%`} accent="#f59e0b" />
              <StatCard label="Market Health" value={`${(stats.market_health * 100).toFixed(0)}%`} accent="#f59e0b" />
              <StatCard label="Active Trades" value={String(stats.active_trades)} accent="#f59e0b" />
            </div>
          ) : (
            <p style={{ color: '#888' }}>No statistics available</p>
          )}

          {/* Economy Snapshot */}
          {snapshot && (
            <>
              <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Current Snapshot</h3>
              <div style={{
                padding: '12px 16px',
                background: '#1a1a2e',
                borderRadius: 8,
                border: '1px solid #2a2a3e',
                display: 'flex',
                gap: 32,
                flexWrap: 'wrap',
              }}>
                <div>
                  <div style={{ fontSize: 10, color: '#666' }}>GDP</div>
                  <div style={{ fontSize: 14, color: '#f59e0b', fontWeight: 600 }}>{snapshot.gdp.toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#666' }}>Gini</div>
                  <div style={{ fontSize: 14, color: '#f59e0b', fontWeight: 600 }}>{snapshot.gini.toFixed(3)}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#666' }}>Inflation</div>
                  <div style={{ fontSize: 14, color: '#f59e0b', fontWeight: 600 }}>{(snapshot.inflation * 100).toFixed(1)}%</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#666' }}>Timestamp</div>
                  <div style={{ fontSize: 14, color: '#888' }}>{snapshot.timestamp}</div>
                </div>
              </div>
            </>
          )}

          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Simulation Control</h3>
          <button onClick={handleSimulateTick} style={buttonStyle('#f59e0b')}>
            Simulate Tick
          </button>
        </div>
      )}

      {/* Market Tab */}
      {activeTab === 'market' && (
        <div>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>Add Market Item</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
            <input
              type="text"
              value={itemName}
              onChange={(e) => setItemName(e.target.value)}
              placeholder="Item name"
              style={inputStyle}
            />
            <select value={itemCategory} onChange={(e) => setItemCategory(e.target.value)} style={selectStyle}>
              {ITEM_CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <input
              type="number"
              value={itemBasePrice}
              onChange={(e) => setItemBasePrice(e.target.value)}
              placeholder="Base price"
              style={{ ...inputStyle, width: 100 }}
              min="1"
            />
            <button onClick={handleAddMarketItem} style={buttonStyle('#f59e0b')}>Add</button>
          </div>

          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>
            Market Items ({marketItems.length})
          </h3>
          {marketItems.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {marketItems.map((item) => (
                <div key={item.id} style={{
                  padding: '10px 14px',
                  background: '#1a1a2e',
                  borderRadius: 6,
                  fontSize: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center', flex: 1 }}>
                    <span style={{ color: '#f59e0b', fontFamily: 'monospace' }}>{item.name}</span>
                    <span style={{
                      padding: '2px 8px',
                      background: '#2a2a3e',
                      borderRadius: 3,
                      fontSize: 10,
                      color: '#aaa',
                    }}>{item.category}</span>
                    <span style={{ color: '#ccc', fontWeight: 600 }}>
                      {item.current_price.toLocaleString()}
                    </span>
                    <span style={{ color: getTrendColor(item.trend), fontSize: 10 }}>
                      {getTrendIcon(item.trend)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 16, color: '#888' }}>
                    <span>S: {item.supply.toLocaleString()}</span>
                    <span>D: {item.demand.toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No market items</p>
          )}
        </div>
      )}

      {/* Currencies Tab */}
      {activeTab === 'currencies' && (
        <div>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>
            Currencies ({currencies.length})
          </h3>
          {currencies.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {currencies.map((currency) => (
                <div key={currency.code} style={{
                  padding: '10px 14px',
                  background: '#1a1a2e',
                  borderRadius: 6,
                  fontSize: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span style={{ color: '#f59e0b', fontFamily: 'monospace', fontWeight: 600 }}>
                      {currency.code}
                    </span>
                    <span style={{ color: '#ccc' }}>{currency.name}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 24, color: '#888' }}>
                    <span>Rate: {currency.exchange_rate.toFixed(4)}</span>
                    <span>Supply: {currency.supply.toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No currencies available</p>
          )}
        </div>
      )}

      {/* Imbalances Tab */}
      {activeTab === 'imbalances' && (
        <div>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>
            Detected Imbalances ({imbalances.length})
          </h3>
          {imbalances.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {imbalances.map((imb) => (
                <div key={imb.id} style={{
                  padding: '10px 14px',
                  background: '#1a1a2e',
                  borderRadius: 6,
                  fontSize: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: getSeverityColor(imb.severity),
                      display: 'inline-block',
                    }} />
                    <span style={{ color: '#ccc' }}>{imb.description}</span>
                    <span style={{ color: '#666' }}>in {imb.affected_market}</span>
                  </div>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: 3,
                    fontSize: 10,
                    color: getSeverityColor(imb.severity),
                    background: getSeverityColor(imb.severity) + '22',
                    border: `1px solid ${getSeverityColor(imb.severity)}44`,
                  }}>
                    {imb.severity}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No imbalances detected</p>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{
      padding: '14px 16px',
      background: '#1a1a2e',
      borderRadius: 8,
      border: '1px solid #2a2a3e',
    }}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: accent }}>{value}</div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '6px 10px',
  background: '#0f0f23',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#e0e0e0',
  fontSize: 12,
  width: 140,
};

const selectStyle: React.CSSProperties = {
  padding: '6px 10px',
  background: '#0f0f23',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#e0e0e0',
  fontSize: 12,
};

const buttonStyle = (accent: string): React.CSSProperties => ({
  padding: '6px 14px',
  background: accent,
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 500,
});