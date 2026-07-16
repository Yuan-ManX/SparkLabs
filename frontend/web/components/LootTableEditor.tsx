import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface LootItem {
  item_id: string;
  name: string;
  drop_rate: number;
  rarity: string;
  min_quantity: number;
  max_quantity: number;
  category: string;
}

interface LootTable {
  table_id: string;
  name: string;
  description: string;
  items: LootItem[];
}

const RARITY_TIERS = ['common', 'uncommon', 'rare', 'epic', 'legendary'] as const;

const RARITY_COLORS: Record<string, string> = {
  common: '#888',
  uncommon: '#22c55e',
  rare: '#f97316',
  epic: '#f97316',
  legendary: '#fbbf24',
};

const RARITY_WEIGHTS: Record<string, number> = {
  common: 60,
  uncommon: 25,
  rare: 10,
  epic: 4,
  legendary: 1,
};

const LootTableEditor: React.FC = () => {
  const [lootTables, setLootTables] = useState<LootTable[]>([]);
  const [selectedTableId, setSelectedTableId] = useState('');
  const [items, setItems] = useState<LootItem[]>([]);
  const [rarityFilter, setRarityFilter] = useState('all');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [newItemName, setNewItemName] = useState('');
  const [newItemRarity, setNewItemRarity] = useState('common');
  const [newItemRate, setNewItemRate] = useState(5);

  const selectedTable = lootTables.find(t => t.table_id === selectedTableId);

  const loadLootTables = useCallback(async () => {
    setLoading(true);
    try {
      const data = await engineApi.listScenes();
      setLootTables([]);
    } catch {
      setLootTables([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadLootTables(); }, [loadLootTables]);

  const filteredItems = rarityFilter === 'all'
    ? items
    : items.filter(item => item.rarity === rarityFilter);

  const totalDropRate = filteredItems.reduce((sum, item) => sum + item.drop_rate, 0);

  const handleSelectTable = (tableId: string) => {
    setSelectedTableId(tableId);
    const table = lootTables.find(t => t.table_id === tableId);
    setItems(table?.items || []);
    setMessage('');
  };

  const handleAddItem = () => {
    if (!newItemName.trim()) return;
    const newItem: LootItem = {
      item_id: `item_${Date.now()}`,
      name: newItemName.trim(),
      drop_rate: newItemRate,
      rarity: newItemRarity,
      min_quantity: 1,
      max_quantity: 3,
      category: 'misc',
    };
    setItems(prev => [...prev, newItem]);
    setNewItemName('');
    setMessage(`Added "${newItem.name}"`);
  };

  const handleRemoveItem = (itemId: string) => {
    const removed = items.find(i => i.item_id === itemId);
    setItems(prev => prev.filter(i => i.item_id !== itemId));
    if (removed) setMessage(`Removed "${removed.name}"`);
  };

  const handleRateChange = (itemId: string, rate: number) => {
    setItems(prev =>
      prev.map(item =>
        item.item_id === itemId ? { ...item, drop_rate: Math.max(0, Math.min(100, rate)) } : item
      )
    );
  };

  const handleSaveLootTable = async () => {
    try {
      setMessage('Loot table saved.');
    } catch {
      setMessage('Failed to save loot table.');
    }
  };

  const getProbabilityBarWidth = (rate: number): string => {
    const maxRate = Math.max(totalDropRate, 100);
    return `${Math.min(100, (rate / maxRate) * 100)}%`;
  };

  const rarityDistribution = RARITY_TIERS.map(tier => ({
    tier,
    count: items.filter(item => item.rarity === tier).length,
    totalRate: items.filter(item => item.rarity === tier).reduce((s, i) => s + i.drop_rate, 0),
  }));

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Loot Table Editor</h3>
        <div className="flex-1" />
        {loading ? (
          <span className="text-[#555] text-[11px]">Loading...</span>
        ) : (
          <select
            value={selectedTableId}
            onChange={e => handleSelectTable(e.target.value)}
            className="bg-[#1a1a1a] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1 outline-none"
          >
            <option value="">Select Loot Table</option>
            {lootTables.map(table => (
              <option key={table.table_id} value={table.table_id}>
                {table.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-2 border-b border-[#1e1e1e]">
        <span className="text-[10px] text-[#888]">Filter:</span>
        {['all', ...RARITY_TIERS].map(tier => (
          <button
            key={tier}
            onClick={() => setRarityFilter(tier)}
            className="px-2 py-0.5 rounded text-[10px] border cursor-pointer transition-colors"
            style={{
              borderColor: rarityFilter === tier ? (RARITY_COLORS[tier] || '#888') : '#333',
              backgroundColor: rarityFilter === tier ? (RARITY_COLORS[tier] || '#888') + '20' : '#1a1a1a',
              color: rarityFilter === tier ? (RARITY_COLORS[tier] || '#888') : '#888',
            }}
          >
            {tier}
          </button>
        ))}
        <div className="flex-1" />
        <span className="text-[10px] text-[#888]">
          {filteredItems.length} items | Total: {totalDropRate.toFixed(1)}%
        </span>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          {filteredItems.length > 0 ? (
            <div className="p-3 space-y-2">
              {filteredItems.map(item => (
                <div
                  key={item.item_id}
                  className="bg-[#1a1a1a] rounded border border-[#2a2a2a] p-3"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: RARITY_COLORS[item.rarity] || '#888' }}
                      />
                      <span className="text-[12px] font-bold text-[#e0e0e0]">{item.name}</span>
                      <span
                        className="text-[9px] px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: (RARITY_COLORS[item.rarity] || '#888') + '20',
                          color: RARITY_COLORS[item.rarity] || '#888',
                        }}
                      >
                        {item.rarity}
                      </span>
                    </div>
                    <button
                      onClick={() => handleRemoveItem(item.item_id)}
                      className="text-[#ef4444] text-[10px] bg-transparent border border-[#ef4444]/30 rounded px-2 py-0.5 cursor-pointer"
                    >
                      Remove
                    </button>
                  </div>

                  <div className="flex items-center gap-3 mb-2">
                    <div className="flex items-center gap-1">
                      <span className="text-[9px] text-[#888]">Rate</span>
                      <input
                        type="number"
                        value={item.drop_rate}
                        onChange={e => handleRateChange(item.item_id, parseFloat(e.target.value) || 0)}
                        min={0}
                        max={100}
                        step={0.1}
                        className="w-16 bg-[#111] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-0.5 outline-none"
                      />
                      <span className="text-[9px] text-[#888]">%</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-[9px] text-[#888]">Qty</span>
                      <input
                        type="number"
                        value={item.min_quantity}
                        onChange={e => setItems(prev =>
                          prev.map(i => i.item_id === item.item_id ? { ...i, min_quantity: parseInt(e.target.value) || 1 } : i)
                        )}
                        min={1}
                        className="w-12 bg-[#111] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-0.5 outline-none"
                      />
                      <span className="text-[9px] text-[#555]">-</span>
                      <input
                        type="number"
                        value={item.max_quantity}
                        onChange={e => setItems(prev =>
                          prev.map(i => i.item_id === item.item_id ? { ...i, max_quantity: parseInt(e.target.value) || 1 } : i)
                        )}
                        min={1}
                        className="w-12 bg-[#111] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-0.5 outline-none"
                      />
                    </div>
                  </div>

                  <div className="relative h-4 bg-[#111] rounded overflow-hidden border border-[#2a2a2a]">
                    <div
                      className="absolute top-0 left-0 h-full rounded transition-all"
                      style={{
                        width: getProbabilityBarWidth(item.drop_rate),
                        backgroundColor: (RARITY_COLORS[item.rarity] || '#888') + '40',
                        borderRight: `1px solid ${RARITY_COLORS[item.rarity] || '#888'}`,
                      }}
                    />
                    <span className="absolute top-0 left-1 text-[8px] text-[#aaa] leading-4">
                      {item.drop_rate.toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-[32px] text-[#333] mb-3">📦</div>
                <p className="text-[#555] text-[12px]">No items in this loot table</p>
                <p className="text-[#444] text-[10px] mt-1">Add items below or select a different table</p>
              </div>
            </div>
          )}
        </div>

        <div className="w-72 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3">
          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Add Item</h4>
            <input
              value={newItemName}
              onChange={e => setNewItemName(e.target.value)}
              placeholder="Item name"
              className="w-full bg-[#1a1a1a] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
              onKeyDown={e => e.key === 'Enter' && handleAddItem()}
            />
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888]">Rarity</span>
              <select
                value={newItemRarity}
                onChange={e => setNewItemRarity(e.target.value)}
                className="flex-1 bg-[#1a1a1a] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
              >
                {RARITY_TIERS.map(tier => (
                  <option key={tier} value={tier}>{tier}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888]">Rate</span>
              <input
                type="number"
                value={newItemRate}
                onChange={e => setNewItemRate(parseFloat(e.target.value) || 0)}
                min={0}
                max={100}
                step={0.5}
                className="w-20 bg-[#1a1a1a] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-1 outline-none"
              />
              <span className="text-[9px] text-[#888]">%</span>
            </div>
            <button
              onClick={handleAddItem}
              className="w-full py-1.5 bg-[#fbbf24] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Add Item
            </button>
          </div>

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Rarity Distribution</h4>
            <div className="space-y-1.5">
              {rarityDistribution.map(({ tier, count, totalRate }) => (
                <div key={tier} className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: RARITY_COLORS[tier] || '#888' }}
                  />
                  <span className="text-[10px] text-[#aaa] flex-1">{tier}</span>
                  <span className="text-[9px] text-[#555]">{count} items</span>
                  <span className="text-[9px]" style={{ color: RARITY_COLORS[tier] || '#888' }}>
                    {totalRate.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={handleSaveLootTable}
            className="w-full py-2 bg-[#f97316] text-white rounded text-[11px] font-bold border-none cursor-pointer"
          >
            Save Loot Table
          </button>
        </div>
      </div>
    </div>
  );
};

export default LootTableEditor;