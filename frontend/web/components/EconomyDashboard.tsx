import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface WalletEntry {
  currency: string;
  balance: number;
  symbol: string;
}

interface MarketItem {
  item_id: string;
  name: string;
  current_price: number;
  supply: number;
  demand: number;
  price_trend: string;
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  gold: '\U0001FA99', silver: '\u2728', copper: '\U0001FAA8',
  crystal: '\U0001F48E', token: '\U0001F4BF', essence: '\u2726',
};

const TREND_COLORS: Record<string, string> = {
  rising: '#10b981', falling: '#ef4444', stable: '#888',
};

const EconomyDashboard: React.FC = () => {
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [wallet, setWallet] = useState<WalletEntry[]>([]);
  const [ownerId, setOwnerId] = useState('player1');
  const [market, setMarket] = useState<MarketItem[]>([]);
  const [message, setMessage] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const data = await engineApi.economyStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ wallets: 0, transactions: 0, inflation_rate: 0 });
    }
  }, []);

  const loadWallet = useCallback(async () => {
    try {
      const data = await engineApi.economyWallet(ownerId);
      setWallet(((data as any).currencies || (data as any).balances || data) as WalletEntry[]);
    } catch { setWallet([]); }
  }, [ownerId]);

  const loadMarket = useCallback(async () => {
    try {
      const data = await engineApi.economyMarket();
      setMarket(((data as any).market || (data as any).items || data) as MarketItem[]);
    } catch { setMarket([]); }
  }, []);

  useEffect(() => { loadStats(); loadWallet(); loadMarket(); }, [loadStats, loadWallet, loadMarket]);

  const handleAddCurrency = async (currency: string, amount: number) => {
    try {
      await engineApi.economyAdd(ownerId, currency, amount);
      setMessage(`Added ${amount} ${currency}`);
      loadWallet();
      loadStats();
    } catch { setMessage('Failed to add currency.'); }
  };

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#fbbf24' }}>Economy Dashboard</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Wallets</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.wallets || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Trades</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.transactions || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Inflation</div>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: (stats.inflation_rate || 0) > 0.05 ? '#ef4444' : '#10b981' }}>
              {((stats.inflation_rate || 0) * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: '#aaa', marginBottom: 6 }}>Wallet ({ownerId})</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {['gold', 'silver', 'copper', 'crystal', 'token', 'essence'].map(currency => (
            <div key={currency} style={{
              padding: '8px 12px', background: '#1a1a2e', borderRadius: 6,
              display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 80,
            }}>
              <span style={{ fontSize: 20 }}>{CURRENCY_SYMBOLS[currency] || '\u26A1'}</span>
              <span style={{ fontSize: 10, color: '#888' }}>{currency}</span>
              <span style={{ fontSize: 14, fontWeight: 'bold', color: '#fbbf24' }}>
                {wallet.find(w => w.currency === currency)?.balance?.toFixed(0) || '0'}
              </span>
              <button onClick={() => handleAddCurrency(currency, 100)} style={{
                marginTop: 4, padding: '2px 8px', borderRadius: 4, border: 'none',
                background: '#fbbf24', color: '#1a1a2e', cursor: 'pointer', fontSize: 10,
              }}>
                +100
              </button>
            </div>
          ))}
        </div>
      </div>

      {market.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>Market ({market.length} items)</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 6 }}>
            {market.slice(0, 12).map((item, i) => (
              <div key={i} style={{
                padding: '8px 10px', background: '#1a1a2e', borderRadius: 6, fontSize: 11,
              }}>
                <div style={{ color: '#e0e0e0', fontWeight: 'bold', marginBottom: 2 }}>{item.name}</div>
                <div style={{ color: '#fbbf24' }}>{item.current_price?.toFixed(0) || 0}g</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                  <span style={{ color: '#888', fontSize: 10 }}>S: {item.supply || 0}</span>
                  <span style={{ color: '#888', fontSize: 10 }}>D: {item.demand || 0}</span>
                  <span style={{ color: TREND_COLORS[item.price_trend || 'stable'] || '#888', fontSize: 10 }}>
                    {item.price_trend || 'stable'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {message && (
        <div style={{ marginTop: 10, padding: 6, background: '#1a2a1a', borderRadius: 4, color: '#10b981', fontSize: 11 }}>
          {message}
        </div>
      )}
    </div>
  );
};

export default EconomyDashboard;