"use client";
import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/agent';

const CURRENCY_TYPES = ['gold', 'gems', 'credits', 'tokens', 'essence', 'souls', 'crystals', 'reputation', 'honor', 'energy'];
const TRANSACTION_TYPES = ['earn', 'spend', 'transfer', 'tax', 'interest', 'reward', 'penalty', 'refund', 'trade'];

export default function AgentEconomyBalancerPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Create currency form
  const [currName, setCurrName] = useState('');
  const [currType, setCurrType] = useState('gold');
  const [currSupply, setCurrSupply] = useState('100000');

  // Transaction form
  const [txPlayerId, setTxPlayerId] = useState('');
  const [txCurrencyId, setTxCurrencyId] = useState('');
  const [txType, setTxType] = useState('earn');
  const [txAmount, setTxAmount] = useState('100');
  const [txDescription, setTxDescription] = useState('');

  // Market item form
  const [miName, setMiName] = useState('');
  const [miCategory, setMiCategory] = useState('');
  const [miBasePrice, setMiBasePrice] = useState('100');
  const [miSupply, setMiSupply] = useState('1000');

  // Simulate form
  const [simCycles, setSimCycles] = useState('10');

  // Balance rewards form
  const [brActivityType, setBrActivityType] = useState('');
  const [brDifficulty, setBrDifficulty] = useState('normal');
  const [brTargetValue, setBrTargetValue] = useState('100');

  const tabs = ['overview', 'currencies', 'market', 'simulate', 'analyze'];

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/economy-balancer/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
  }, []);

  useEffect(() => { fetchStats(); const i = setInterval(fetchStats, 15000); return () => clearInterval(i); }, [fetchStats]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.error || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const handleGet = async (url: string) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url);
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || 'Failed');
      fetchStats();
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const inputCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-[#00d4ff]';
  const selectCls = 'w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white outline-none focus:border-[#00d4ff]';
  const cardCls = 'bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]';

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-gray-300 hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {message && (
        <div className="mx-4 mt-2 p-2 rounded text-sm border bg-[#0f0f23] border-[#00ff88] text-[#00ff88]">{message}</div>
      )}

      <div className="flex-1 overflow-auto p-4">

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00d4ff]">Economy Balancer Overview</h2>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Currencies', value: stats.total_currencies, color: 'text-[#00d4ff]' },
                { label: 'Total Transactions', value: stats.total_transactions, color: 'text-[#00ff88]' },
                { label: 'Market Items', value: stats.total_market_items, color: 'text-amber-300' },
                { label: 'Economy State', value: stats.economy_state, color: 'text-pink-300' },
              ].map(s => (
                <div key={s.label} className="bg-[#0f0f23] p-4 rounded border border-[#2a2a4a]">
                  <h3 className="text-xs text-gray-400">{s.label}</h3>
                  <p className={`text-2xl font-bold ${s.color}`}>{s.value ?? 0}</p>
                </div>
              ))}
            </div>
            {Object.keys(stats).length > 0 && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-gray-300 mb-2">Detailed Stats</h3>
                <pre className="text-xs text-gray-400 overflow-auto max-h-48">{JSON.stringify(stats, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* CURRENCIES TAB */}
        {activeTab === 'currencies' && (
          <div className="space-y-6">
            <h2 className="text-lg font-bold text-[#00d4ff]">Create Currency</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Currency Name" value={currName} onChange={e => setCurrName(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={currType} onChange={e => setCurrType(e.target.value)}>
                  {CURRENCY_TYPES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                </select>
                <input className={inputCls} placeholder="Initial Supply" type="number" value={currSupply} onChange={e => setCurrSupply(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/economy-balancer/create-currency`, {
                  name: currName, currency_type: currType, initial_supply: parseInt(currSupply),
                })}>
                {loading ? 'Creating...' : 'Create Currency'}
              </button>
            </div>

            <h2 className="text-lg font-bold text-[#00ff88]">Record Transaction</h2>
            <div className={cardCls + ' space-y-3'}>
              <div className="grid grid-cols-2 gap-3">
                <input className={inputCls} placeholder="Player ID" value={txPlayerId} onChange={e => setTxPlayerId(e.target.value)} />
                <input className={inputCls} placeholder="Currency ID" value={txCurrencyId} onChange={e => setTxCurrencyId(e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={txType} onChange={e => setTxType(e.target.value)}>
                  {TRANSACTION_TYPES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                </select>
                <input className={inputCls} placeholder="Amount" type="number" value={txAmount} onChange={e => setTxAmount(e.target.value)} />
              </div>
              <input className={inputCls} placeholder="Description" value={txDescription} onChange={e => setTxDescription(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/economy-balancer/record-transaction`, {
                  player_id: txPlayerId, currency_id: txCurrencyId, transaction_type: txType,
                  amount: parseInt(txAmount), description: txDescription,
                })}>
                {loading ? 'Recording...' : 'Record Transaction'}
              </button>
            </div>
          </div>
        )}

        {/* MARKET TAB */}
        {activeTab === 'market' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-amber-300">Add Market Item</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Item Name" value={miName} onChange={e => setMiName(e.target.value)} />
              <div className="grid grid-cols-3 gap-3">
                <input className={inputCls} placeholder="Category" value={miCategory} onChange={e => setMiCategory(e.target.value)} />
                <input className={inputCls} placeholder="Base Price" type="number" value={miBasePrice} onChange={e => setMiBasePrice(e.target.value)} />
                <input className={inputCls} placeholder="Supply" type="number" value={miSupply} onChange={e => setMiSupply(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/economy-balancer/add-market-item`, {
                  name: miName, category: miCategory, base_price: parseFloat(miBasePrice), supply: parseInt(miSupply),
                })}>
                {loading ? 'Adding...' : 'Add Market Item'}
              </button>
            </div>

            {result && activeTab === 'market' && (
              <div className={cardCls}>
                <h3 className="text-sm font-bold text-gray-300 mb-3">Market Items</h3>
                {Array.isArray(result.items) ? (
                  <div className="space-y-2">
                    {result.items.map((item: any, i: number) => (
                      <div key={i} className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] flex justify-between items-center">
                        <div>
                          <span className="text-sm text-white">{item.name}</span>
                          <span className="text-xs text-gray-500 ml-2">{item.category}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-sm text-amber-300">${item.current_price ?? item.base_price}</span>
                          <span className="text-xs text-gray-500 ml-2">x{item.supply}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <pre className="text-xs text-gray-400 overflow-auto">{JSON.stringify(result, null, 2)}</pre>
                )}
              </div>
            )}
          </div>
        )}

        {/* SIMULATE TAB */}
        {activeTab === 'simulate' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-[#00ff88]">Simulate Market</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Cycles" type="number" value={simCycles} onChange={e => setSimCycles(e.target.value)} />
              <button
                className="w-full px-4 py-2 bg-[#00ff88] text-black rounded text-sm font-medium hover:bg-[#00cc6a] transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/economy-balancer/simulate-market`, {
                  cycles: parseInt(simCycles),
                })}>
                {loading ? 'Simulating...' : 'Simulate Market'}
              </button>
            </div>

            {result && activeTab === 'simulate' && (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: 'Market Health', value: result.market_health, color: 'text-[#00ff88]' },
                    { label: 'Price Changes', value: result.price_changes, color: 'text-amber-300' },
                    { label: 'Transaction Volume', value: result.transaction_volume, color: 'text-[#00d4ff]' },
                  ].map(s => (
                    <div key={s.label} className={cardCls + ' text-center'}>
                      <h3 className="text-xs text-gray-400">{s.label}</h3>
                      <p className={`text-xl font-bold ${s.color}`}>{s.value ?? '--'}</p>
                    </div>
                  ))}
                </div>
                {result.price_history && (
                  <div className={cardCls}>
                    <h3 className="text-sm font-bold text-gray-300 mb-2">Price History</h3>
                    <div className="space-y-1">
                      {(Array.isArray(result.price_history) ? result.price_history : []).map((entry: any, i: number) => (
                        <div key={i} className="flex justify-between bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a] text-xs">
                          <span className="text-gray-400">Cycle {entry.cycle ?? i}</span>
                          <span className="text-amber-300">{entry.price ?? JSON.stringify(entry)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <pre className="bg-[#1a1a2e] p-3 rounded border border-[#2a2a4a] text-xs text-gray-400 overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {/* ANALYZE TAB */}
        {activeTab === 'analyze' && (
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-pink-300">Analyze Economy</h2>
            <div className={cardCls + ' space-y-3'}>
              <button
                className="w-full px-4 py-2 bg-pink-500 text-white rounded text-sm font-medium hover:bg-pink-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handleGet(`${API_BASE}/economy-balancer/analyze`)}>
                {loading ? 'Analyzing...' : 'Analyze Economy'}
              </button>
            </div>

            {result && activeTab === 'analyze' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: 'Money Supply', value: result.money_supply, color: 'text-[#00d4ff]' },
                    { label: 'Faucet/Sink Ratio', value: result.faucet_sink_ratio, color: 'text-[#00ff88]' },
                  ].map(s => (
                    <div key={s.label} className={cardCls}>
                      <h3 className="text-xs text-gray-400">{s.label}</h3>
                      <p className={`text-xl font-bold ${s.color}`}>{s.value ?? '--'}</p>
                    </div>
                  ))}
                </div>
                {result.per_currency_breakdown && (
                  <div className={cardCls}>
                    <h3 className="text-sm font-bold text-gray-300 mb-2">Per-Currency Breakdown</h3>
                    <div className="space-y-2">
                      {Object.entries(result.per_currency_breakdown).map(([k, v]) => (
                        <div key={k} className="bg-[#1a1a2e] p-2 rounded border border-[#2a2a4a] flex justify-between text-xs">
                          <span className="text-gray-400 capitalize">{k}</span>
                          <span className="text-[#00d4ff]">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {result.suggestions && Array.isArray(result.suggestions) && result.suggestions.length > 0 && (
                  <div className={cardCls}>
                    <h3 className="text-sm font-bold text-[#00ff88] mb-2">Suggestions</h3>
                    <ul className="list-disc list-inside text-xs text-gray-300 space-y-1">
                      {result.suggestions.map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <h2 className="text-lg font-bold text-amber-300 mt-6">Balance Rewards</h2>
            <div className={cardCls + ' space-y-3'}>
              <input className={inputCls} placeholder="Activity Type" value={brActivityType} onChange={e => setBrActivityType(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <select className={selectCls} value={brDifficulty} onChange={e => setBrDifficulty(e.target.value)}>
                  <option value="easy">Easy</option>
                  <option value="normal">Normal</option>
                  <option value="hard">Hard</option>
                  <option value="epic">Epic</option>
                </select>
                <input className={inputCls} placeholder="Target Value" type="number" value={brTargetValue} onChange={e => setBrTargetValue(e.target.value)} />
              </div>
              <button
                className="w-full px-4 py-2 bg-amber-500 text-black rounded text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50"
                disabled={loading}
                onClick={() => handlePost(`${API_BASE}/economy-balancer/balance-rewards`, {
                  activity_type: brActivityType, difficulty: brDifficulty, target_value: parseFloat(brTargetValue),
                })}>
                {loading ? 'Balancing...' : 'Balance Rewards'}
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}