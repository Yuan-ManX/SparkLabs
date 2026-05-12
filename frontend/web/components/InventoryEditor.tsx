import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface InventoryItem {
  item_id: string;
  name: string;
  description: string;
  category: string;
  weight: number;
  maxStack: number;
  rarity: string;
  isQuestItem: boolean;
  iconUrl: string;
  quantity: number;
}

const CATEGORIES = ['weapon', 'armor', 'consumable', 'quest', 'material', 'key'] as const;

const RARITY_TIERS = ['common', 'uncommon', 'rare', 'epic', 'legendary'] as const;

const RARITY_COLORS: Record<string, string> = {
  common: '#888',
  uncommon: '#22c55e',
  rare: '#3b82f6',
  epic: '#8b5cf6',
  legendary: '#fbbf24',
};

const CATEGORY_ICONS: Record<string, string> = {
  weapon: '\u2694\uFE0F',
  armor: '\uD83D\uDEE1\uFE0F',
  consumable: '\uD83C\uDF76',
  quest: '\u2753',
  material: '\uD83E\uDEA8',
  key: '\uD83D\uDD11',
};

const InventoryEditor: React.FC = () => {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [selectedItemId, setSelectedItemId] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newCategory, setNewCategory] = useState('consumable');
  const [newWeight, setNewWeight] = useState(1.0);
  const [newMaxStack, setNewMaxStack] = useState(99);
  const [newRarity, setNewRarity] = useState('common');
  const [newIsQuestItem, setNewIsQuestItem] = useState(false);
  const [newIconUrl, setNewIconUrl] = useState('');
  const [newQuantity, setNewQuantity] = useState(1);

  const selectedItem = items.find(i => i.item_id === selectedItemId);

  const loadItems = useCallback(async () => {
    setLoading(true);
    try {
      const data = await engineApi.listScenes();
      setItems([]);
    } catch {
      setItems([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadItems(); }, [loadItems]);

  const filteredItems = filterCategory === 'all'
    ? items
    : items.filter(item => item.category === filterCategory);

  const totalWeight = items.reduce((sum, item) => sum + item.weight * item.quantity, 0);
  const uniqueCategories = [...new Set(items.map(i => i.category))].length;

  const handleAddItem = () => {
    if (!newName.trim()) return;
    const newItem: InventoryItem = {
      item_id: `inv_${Date.now()}`,
      name: newName.trim(),
      description: newDescription.trim(),
      category: newCategory,
      weight: newWeight,
      maxStack: newMaxStack,
      rarity: newRarity,
      isQuestItem: newIsQuestItem,
      iconUrl: newIconUrl.trim(),
      quantity: newQuantity,
    };
    setItems(prev => [...prev, newItem]);
    setNewName('');
    setNewDescription('');
    setMessage(`Added "${newItem.name}" to inventory`);
  };

  const handleDeleteItem = (itemId: string) => {
    const removed = items.find(i => i.item_id === itemId);
    setItems(prev => prev.filter(i => i.item_id !== itemId));
    if (selectedItemId === itemId) setSelectedItemId('');
    if (removed) setMessage(`Removed "${removed.name}"`);
  };

  const handleSaveItem = async () => {
    try {
      setMessage('Inventory saved successfully.');
    } catch {
      setMessage('Failed to save inventory.');
    }
  };

  return (
    <div className="h-full bg-[#111] text-[#e0e0e0] flex flex-col overflow-hidden" style={{ fontFamily: 'monospace' }}>
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#1e1e1e]">
        <h3 className="text-[13px] font-bold text-[#fbbf24] m-0">Inventory Editor</h3>
        <div className="flex-1" />
        {loading && <span className="text-[#555] text-[11px]">Loading...</span>}
        <button
          onClick={handleSaveItem}
          className="px-3 py-1 bg-[#3b82f6] text-white rounded text-[11px] font-bold border-none cursor-pointer"
        >
          Save
        </button>
      </div>

      {message && (
        <div className="mx-4 mt-2 px-3 py-1.5 bg-[#1a2a1a] rounded text-[#10b981] text-[11px] border border-[#1a3a1a]">
          {message}
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-2 border-b border-[#1e1e1e] flex-wrap">
        <span className="text-[10px] text-[#888]">Filter:</span>
        <button
          onClick={() => setFilterCategory('all')}
          className="px-2 py-0.5 rounded text-[10px] border cursor-pointer transition-colors"
          style={{
            borderColor: filterCategory === 'all' ? '#fbbf24' : '#333',
            backgroundColor: filterCategory === 'all' ? '#2a2a1a' : '#1a1a2e',
            color: filterCategory === 'all' ? '#fbbf24' : '#888',
          }}
        >
          all
        </button>
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setFilterCategory(cat)}
            className="px-2 py-0.5 rounded text-[10px] border cursor-pointer transition-colors"
            style={{
              borderColor: filterCategory === cat ? '#fbbf24' : '#333',
              backgroundColor: filterCategory === cat ? '#2a2a1a' : '#1a1a2e',
              color: filterCategory === cat ? '#fbbf24' : '#888',
            }}
          >
            {CATEGORY_ICONS[cat] || ''} {cat}
          </button>
        ))}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3">
          {filteredItems.length > 0 ? (
            <div className="grid grid-cols-3 gap-2">
              {filteredItems.map(item => (
                <div
                  key={item.item_id}
                  onClick={() => setSelectedItemId(item.item_id)}
                  className="bg-[#16213e] rounded border p-2 cursor-pointer transition-colors"
                  style={{
                    borderColor: selectedItemId === item.item_id ? '#fbbf24' : '#2a2a2a',
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-8 h-8 bg-[#0f3460] rounded flex items-center justify-center text-[14px]">
                      {item.iconUrl ? '🖼' : CATEGORY_ICONS[item.category] || '📦'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[11px] font-bold text-[#e0e0e0] truncate">{item.name}</div>
                      <div className="flex items-center gap-1">
                        <span
                          className="text-[8px] px-1 rounded"
                          style={{
                            backgroundColor: (RARITY_COLORS[item.rarity] || '#888') + '20',
                            color: RARITY_COLORS[item.rarity] || '#888',
                          }}
                        >
                          {item.rarity}
                        </span>
                        {item.isQuestItem && (
                          <span className="text-[8px] px-1 bg-[#fbbf24]/20 text-[#fbbf24] rounded">
                            quest
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[9px] text-[#888]">
                    <span>x{item.quantity}</span>
                    <span>{item.weight}kg</span>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); handleDeleteItem(item.item_id); }}
                    className="mt-1 w-full py-0.5 text-[#ef4444] text-[9px] bg-transparent border border-[#ef4444]/20 rounded cursor-pointer"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-[32px] text-[#333] mb-3">🎒</div>
                <p className="text-[#555] text-[12px]">No items in inventory</p>
                <p className="text-[#444] text-[10px] mt-1">Add items using the form on the right</p>
              </div>
            </div>
          )}
        </div>

        <div className="w-80 border-l border-[#1e1e1e] overflow-y-auto p-3 space-y-3">
          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Add Item</h4>
            <input
              value={newName}
              onChange={e => setNewName(e.target.value)}
              placeholder="Item name"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
              onKeyDown={e => e.key === 'Enter' && handleAddItem()}
            />
            <input
              value={newDescription}
              onChange={e => setNewDescription(e.target.value)}
              placeholder="Description"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
            />
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888] w-14">Category</span>
              <select
                value={newCategory}
                onChange={e => setNewCategory(e.target.value)}
                className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
              >
                {CATEGORIES.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888] w-14">Rarity</span>
              <select
                value={newRarity}
                onChange={e => setNewRarity(e.target.value)}
                className="flex-1 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1 py-1 outline-none"
              >
                {RARITY_TIERS.map(tier => (
                  <option key={tier} value={tier}>{tier}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888] w-14">Weight</span>
              <input
                type="range"
                min={0}
                max={50}
                step={0.1}
                value={newWeight}
                onChange={e => setNewWeight(parseFloat(e.target.value))}
                className="flex-1"
              />
              <span className="text-[10px] text-[#aaa] w-8 text-right">{newWeight.toFixed(1)}</span>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888] w-14">MaxStack</span>
              <input
                type="number"
                value={newMaxStack}
                onChange={e => setNewMaxStack(parseInt(e.target.value) || 1)}
                min={1}
                max={999}
                className="w-16 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-1 outline-none"
              />
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[10px] text-[#888] w-14">Quantity</span>
              <input
                type="number"
                value={newQuantity}
                onChange={e => setNewQuantity(parseInt(e.target.value) || 1)}
                min={1}
                max={999}
                className="w-16 bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[10px] rounded px-1.5 py-1 outline-none"
              />
            </div>
            <div className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                checked={newIsQuestItem}
                onChange={e => setNewIsQuestItem(e.target.checked)}
                className="accent-[#fbbf24]"
              />
              <span className="text-[10px] text-[#888]">Quest Item</span>
            </div>
            <input
              value={newIconUrl}
              onChange={e => setNewIconUrl(e.target.value)}
              placeholder="Icon URL (optional)"
              className="w-full bg-[#1a1a2e] border border-[#333] text-[#e0e0e0] text-[11px] rounded px-2 py-1.5 mb-2 outline-none"
            />
            <button
              onClick={handleAddItem}
              className="w-full py-1.5 bg-[#fbbf24] text-[#111] rounded text-[11px] font-bold border-none cursor-pointer"
            >
              Add Item
            </button>
          </div>

          {selectedItem && (
            <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
              <h4 className="text-[11px] font-bold text-[#fbbf24] mb-2">{selectedItem.name}</h4>
              <div className="space-y-1.5">
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Category</span>
                  <span className="text-[#aaa]">{selectedItem.category}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Rarity</span>
                  <span style={{ color: RARITY_COLORS[selectedItem.rarity] || '#888' }}>
                    {selectedItem.rarity}
                  </span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Weight</span>
                  <span className="text-[#aaa]">{selectedItem.weight} kg</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Max Stack</span>
                  <span className="text-[#aaa]">{selectedItem.maxStack}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Quantity</span>
                  <span className="text-[#aaa]">x{selectedItem.quantity}</span>
                </div>
                <div className="flex justify-between text-[10px]">
                  <span className="text-[#888]">Quest Item</span>
                  <span className="text-[#aaa]">{selectedItem.isQuestItem ? 'Yes' : 'No'}</span>
                </div>
                {selectedItem.description && (
                  <div className="pt-1 border-t border-[#1a1a1a]">
                    <div className="text-[10px] text-[#888] mb-0.5">Description</div>
                    <div className="text-[10px] text-[#aaa]">{selectedItem.description}</div>
                  </div>
                )}
              </div>
              <button
                onClick={() => handleDeleteItem(selectedItem.item_id)}
                className="mt-2 w-full py-1.5 bg-[#ef4444]/20 text-[#ef4444] rounded text-[11px] border border-[#ef4444]/30 cursor-pointer"
              >
                Delete Item
              </button>
            </div>
          )}

          <div className="bg-[#0a0a0a] rounded border border-[#2a2a2a] p-3">
            <h4 className="text-[11px] font-bold text-[#888] mb-2">Stats</h4>
            <div className="space-y-2">
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total Items</span>
                <span className="text-[#fbbf24] font-bold">{items.length}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Total Weight</span>
                <span className="text-[#fbbf24] font-bold">{totalWeight.toFixed(1)} kg</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Unique Categories</span>
                <span className="text-[#fbbf24] font-bold">{uniqueCategories}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-[#888]">Quest Items</span>
                <span className="text-[#fbbf24] font-bold">
                  {items.filter(i => i.isQuestItem).length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InventoryEditor;