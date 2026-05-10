import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface Recipe {
  recipe_id: string;
  name: string;
  description: string;
  category: string;
  quality: string;
  skill_required: number;
  ingredients: { item_id: string; item_name: string; quantity: number }[];
  result_item: string;
}

const QUALITY_COLORS: Record<string, string> = {
  crude: '#888', common: '#aaa', fine: '#10b981',
  superior: '#3b82f6', exquisite: '#8b5cf6', legendary: '#fbbf24',
};

const CATEGORY_LABELS: Record<string, string> = {
  smithing: '\u2692', alchemy: '\u2697', cooking: '\U0001F373',
  tailoring: '\U0001F9F5', enchanting: '\u2728', engineering: '\u2699', runecrafting: '\u26A1',
};

const CraftingEditor: React.FC = () => {
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [characterId, setCharacterId] = useState('player1');
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [message, setMessage] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const data = await engineApi.craftingStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ recipes_known: 0, crafting_attempts: 0 });
    }
  }, []);

  const loadRecipes = useCallback(async () => {
    try {
      const data = await engineApi.craftingRecipes(characterId);
      setRecipes((data.recipes || data) as Recipe[]);
    } catch {}
  }, [characterId]);

  useEffect(() => { loadStats(); loadRecipes(); }, [loadStats, loadRecipes]);

  const handleCraft = async (recipeId: string) => {
    try {
      const result = await engineApi.craftingCraft(characterId, recipeId);
      setMessage(`Crafted: ${result.result_item || 'item'}`);
      loadStats();
    } catch { setMessage('Crafting failed.'); }
  };

  const filteredRecipes = selectedCategory === 'all'
    ? recipes
    : recipes.filter(r => r.category === selectedCategory);

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#fbbf24' }}>Crafting Editor</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Known</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.recipes_known || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Attempts</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.crafting_attempts || 0}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
        {['all', 'smithing', 'alchemy', 'cooking', 'tailoring', 'enchanting', 'engineering'].map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            style={{
              padding: '4px 10px', borderRadius: 6, fontSize: 11,
              border: selectedCategory === cat ? '2px solid #fbbf24' : '1px solid #333',
              background: selectedCategory === cat ? '#2a2a1a' : '#1a1a2e',
              color: selectedCategory === cat ? '#fbbf24' : '#aaa',
              cursor: 'pointer',
            }}
          >
            {CATEGORY_LABELS[cat] || ''} {cat}
          </button>
        ))}
      </div>

      {message && (
        <div style={{ padding: 6, marginBottom: 10, background: '#1a2a1a', borderRadius: 4, color: '#10b981', fontSize: 11 }}>
          {message}
        </div>
      )}

      {filteredRecipes.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>
            Recipes ({filteredRecipes.length})
          </div>
          {filteredRecipes.slice(0, 15).map(recipe => (
            <div key={recipe.recipe_id} style={{
              padding: '8px 12px', background: '#1a1a2e', borderRadius: 6, marginBottom: 6,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 12 }}>{CATEGORY_LABELS[recipe.category] || ''}</span>
                  <span style={{ fontSize: 13, color: '#e0e0e0', fontWeight: 'bold' }}>{recipe.name}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{
                    padding: '1px 6px', borderRadius: 3, fontSize: 10, fontWeight: 'bold',
                    background: QUALITY_COLORS[recipe.quality] + '33',
                    color: QUALITY_COLORS[recipe.quality] || '#aaa',
                  }}>
                    {recipe.quality}
                  </span>
                  <button onClick={() => handleCraft(recipe.recipe_id)} style={{
                    padding: '3px 10px', borderRadius: 4, border: 'none',
                    background: '#fbbf24', color: '#1a1a2e', cursor: 'pointer', fontSize: 11,
                    fontWeight: 'bold',
                  }}>
                    Craft
                  </button>
                </div>
              </div>
              <div style={{ fontSize: 10, color: '#888' }}>
                {recipe.ingredients?.slice(0, 4).map((ing, i) => (
                  <span key={i} style={{ marginRight: 8 }}>
                    {ing.item_name} x{ing.quantity}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CraftingEditor;