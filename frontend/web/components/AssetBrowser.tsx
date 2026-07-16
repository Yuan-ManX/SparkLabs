import React, { useState, useCallback } from 'react';
import { gameTemplateApi, studioCommandApi } from '../utils/api';

type AssetCategory = 'templates' | 'commands' | 'genres' | 'knowledge';

const CATEGORY_ICONS: Record<string, string> = {
  templates: 'fa-cube',
  commands: 'fa-terminal',
  genres: 'fa-gamepad',
  knowledge: 'fa-brain',
};

const CATEGORY_COLORS: Record<string, string> = {
  templates: '#f97316',
  commands: '#10b981',
  genres: '#f97316',
  knowledge: '#f97316',
};

interface AssetItem {
  id: string;
  name: string;
  category: string;
  description: string;
  tags: string[];
  metadata: Record<string, unknown>;
}

const AssetBrowser: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState<AssetCategory>('templates');
  const [searchQuery, setSearchQuery] = useState('');
  const [items, setItems] = useState<AssetItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<AssetItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadedCategories, setLoadedCategories] = useState<Set<string>>(new Set());

  const loadCategory = useCallback(async (category: AssetCategory) => {
    if (loadedCategories.has(category)) return;
    setLoading(true);
    try {
      let newItems: AssetItem[] = [];
      if (category === 'templates') {
        const data = await gameTemplateApi.list() as Record<string, unknown>;
        const templates = (data.templates as Record<string, unknown>[]) || [];
        newItems = templates.map((t: Record<string, unknown>) => ({
          id: t.id as string,
          name: t.name as string,
          category: 'templates',
          description: t.description as string,
          tags: (t.tags as string[]) || [],
          metadata: t,
        }));
      } else if (category === 'commands') {
        const data = await studioCommandApi.list() as Record<string, unknown>;
        const commands = (data.commands as Record<string, unknown>[]) || [];
        newItems = commands.map((c: Record<string, unknown>) => ({
          id: c.id as string,
          name: c.name as string,
          category: 'commands',
          description: c.description as string,
          tags: (c.tags as string[]) || [],
          metadata: c,
        }));
      } else if (category === 'genres') {
        const data = await gameTemplateApi.genres() as Record<string, unknown>;
        const genres = (data.genres as Record<string, unknown>[]) || [];
        newItems = genres.map((g: Record<string, unknown>) => ({
          id: g.value as string,
          name: g.name as string,
          category: 'genres',
          description: `Game genre: ${g.name}`,
          tags: [g.value as string],
          metadata: g,
        }));
      } else if (category === 'knowledge') {
        newItems = [
          { id: 'game-patterns', name: 'Game Design Patterns', category: 'knowledge', description: 'Common game design patterns and architectures', tags: ['patterns', 'architecture'], metadata: {} },
          { id: 'entity-systems', name: 'Entity Component Systems', category: 'knowledge', description: 'ECS patterns for game entity management', tags: ['ecs', 'components'], metadata: {} },
          { id: 'ai-behaviors', name: 'AI Behavior Trees', category: 'knowledge', description: 'Behavior tree patterns for game AI', tags: ['ai', 'behavior'], metadata: {} },
          { id: 'physics-patterns', name: 'Physics Integration', category: 'knowledge', description: 'Physics engine integration patterns', tags: ['physics', 'collision'], metadata: {} },
          { id: 'audio-patterns', name: 'Audio Systems', category: 'knowledge', description: 'Game audio and sound design patterns', tags: ['audio', 'sound'], metadata: {} },
        ];
      }
      setItems(prev => [...prev.filter(i => i.category !== category), ...newItems]);
      setLoadedCategories(prev => new Set([...prev, category]));
    } catch {
      const fallbackItems: Record<string, AssetItem[]> = {
        templates: [
          { id: 'platformer', name: '2D Platformer', category: 'templates', description: 'Side-scrolling platformer with jumping and collectibles', tags: ['2d', 'side-scroller'], metadata: {} },
          { id: 'rpg', name: 'Turn-Based RPG', category: 'templates', description: 'Turn-based RPG with party management and combat', tags: ['rpg', 'turn-based'], metadata: {} },
          { id: 'shooter', name: 'Top-Down Shooter', category: 'templates', description: 'Top-down shooter with wave-based enemies', tags: ['shooter', 'top-down'], metadata: {} },
          { id: 'puzzle', name: 'Match-3 Puzzle', category: 'templates', description: 'Match-3 puzzle with combos and special pieces', tags: ['puzzle', 'casual'], metadata: {} },
          { id: 'roguelike', name: 'Roguelike Dungeon Crawler', category: 'templates', description: 'Procedural dungeon crawler with permadeath', tags: ['roguelike', 'procedural'], metadata: {} },
          { id: 'survival', name: 'Survival Crafting', category: 'templates', description: 'Survival game with crafting and day-night cycle', tags: ['survival', 'crafting'], metadata: {} },
          { id: 'strategy', name: 'Tower Defense', category: 'templates', description: 'Tower defense with upgrade paths and waves', tags: ['strategy', 'tower-defense'], metadata: {} },
          { id: 'metroidvania', name: 'Metroidvania', category: 'templates', description: 'Exploration platformer with ability gating', tags: ['metroidvania', 'exploration'], metadata: {} },
        ],
        commands: [
          { id: 'cmd-start', name: '/start', category: 'commands', description: 'Initialize a new game project', tags: ['setup', 'onboarding'], metadata: {} },
          { id: 'cmd-brainstorm', name: '/brainstorm', category: 'commands', description: 'Generate creative game concepts', tags: ['creative', 'ideation'], metadata: {} },
          { id: 'cmd-design', name: '/design-system', category: 'commands', description: 'Create detailed game system design', tags: ['design', 'documentation'], metadata: {} },
          { id: 'cmd-dev', name: '/dev-story', category: 'commands', description: 'Implement a user story', tags: ['development', 'implementation'], metadata: {} },
          { id: 'cmd-review', name: '/code-review', category: 'commands', description: 'Review code against standards', tags: ['review', 'quality'], metadata: {} },
          { id: 'cmd-qa', name: '/smoke-check', category: 'commands', description: 'Run quick smoke tests', tags: ['qa', 'testing'], metadata: {} },
          { id: 'cmd-sprint', name: '/sprint-plan', category: 'commands', description: 'Plan the next sprint', tags: ['production', 'planning'], metadata: {} },
          { id: 'cmd-release', name: '/release-checklist', category: 'commands', description: 'Generate pre-release checklist', tags: ['release', 'checklist'], metadata: {} },
        ],
        genres: [
          { id: 'platformer', name: 'Platformer', category: 'genres', description: 'Platformer games', tags: ['platformer'], metadata: {} },
          { id: 'rpg', name: 'RPG', category: 'genres', description: 'Role-playing games', tags: ['rpg'], metadata: {} },
          { id: 'shooter', name: 'Shooter', category: 'genres', description: 'Shooting games', tags: ['shooter'], metadata: {} },
          { id: 'puzzle', name: 'Puzzle', category: 'genres', description: 'Puzzle games', tags: ['puzzle'], metadata: {} },
          { id: 'strategy', name: 'Strategy', category: 'genres', description: 'Strategy games', tags: ['strategy'], metadata: {} },
          { id: 'roguelike', name: 'Roguelike', category: 'genres', description: 'Roguelike games', tags: ['roguelike'], metadata: {} },
          { id: 'survival', name: 'Survival', category: 'genres', description: 'Survival games', tags: ['survival'], metadata: {} },
          { id: 'horror', name: 'Horror', category: 'genres', description: 'Horror games', tags: ['horror'], metadata: {} },
        ],
        knowledge: [
          { id: 'game-patterns', name: 'Game Design Patterns', category: 'knowledge', description: 'Common game design patterns', tags: ['patterns'], metadata: {} },
          { id: 'ecs', name: 'Entity Component Systems', category: 'knowledge', description: 'ECS patterns', tags: ['ecs'], metadata: {} },
          { id: 'ai', name: 'AI Behavior Trees', category: 'knowledge', description: 'Behavior tree patterns', tags: ['ai'], metadata: {} },
        ],
      };
      const fallback = fallbackItems[category] || [];
      setItems(prev => [...prev.filter(i => i.category !== category), ...fallback]);
      setLoadedCategories(prev => new Set([...prev, category]));
    }
    setLoading(false);
  }, [loadedCategories]);

  const handleCategoryChange = (cat: AssetCategory) => {
    setActiveCategory(cat);
    loadCategory(cat);
  };

  const filteredItems = items
    .filter(i => i.category === activeCategory)
    .filter(i => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      return i.name.toLowerCase().includes(q) || i.description.toLowerCase().includes(q) || i.tags.some(t => t.toLowerCase().includes(q));
    });

  const categories: { id: AssetCategory; label: string }[] = [
    { id: 'templates', label: 'Templates' },
    { id: 'commands', label: 'Commands' },
    { id: 'genres', label: 'Genres' },
    { id: 'knowledge', label: 'Knowledge' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#0d0d0d]">
      <div className="px-4 py-3 border-b border-[#1e1e1e]">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg flex items-center justify-center">
            <i className="fa-solid fa-box-archive text-white text-[11px]" />
          </div>
          <div>
            <h2 className="text-[13px] font-bold text-[#e0e0e0]">Asset Browser</h2>
            <p className="text-[9px] text-[#666]">Templates, Commands, Genres & Knowledge</p>
          </div>
        </div>

        <div className="flex gap-1 mb-2">
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => handleCategoryChange(cat.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-medium transition-all ${
                activeCategory === cat.id
                  ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                  : 'text-[#888] hover:text-[#bbb] hover:bg-[#1a1a1a] border border-transparent'
              }`}
            >
              <i className={`fa-solid ${CATEGORY_ICONS[cat.id]} text-[9px]`} />
              {cat.label}
            </button>
          ))}
        </div>

        <div className="relative">
          <i className="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-[10px] text-[#555]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`Search ${activeCategory}...`}
            className="w-full bg-[#0d0d0d] border border-[#2a2a2a] rounded-lg pl-8 pr-3 py-1.5 text-[11px] text-[#ddd] placeholder-[#555] focus:border-orange-500/50 focus:outline-none"
          />
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto p-3">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="flex items-center gap-2 text-[#666]">
                <i className="fa-solid fa-spinner fa-spin" />
                <span className="text-[11px]">Loading...</span>
              </div>
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="flex items-center justify-center h-full text-[#555]">
              <div className="text-center">
                <i className={`fa-solid ${CATEGORY_ICONS[activeCategory]} text-2xl mb-2`} />
                <p className="text-[11px]">No {activeCategory} found</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-1.5">
              {filteredItems.map(item => {
                const color = CATEGORY_COLORS[item.category] || '#666';
                const isSelected = selectedItem?.id === item.id;

                return (
                  <div
                    key={item.id}
                    onClick={() => setSelectedItem(isSelected ? null : item)}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-orange-500/50 bg-orange-500/10'
                        : 'border-[#2a2a2a] bg-[#0d0d0d] hover:border-[#3a3a3a]'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-5 h-5 rounded flex items-center justify-center" style={{ backgroundColor: `${color}20` }}>
                        <i className={`fa-solid ${CATEGORY_ICONS[item.category]} text-[8px]`} style={{ color }} />
                      </div>
                      <span className="text-[11px] font-medium text-[#ddd] flex-1 truncate">{item.name}</span>
                    </div>
                    <div className="text-[9px] text-[#888] mb-1 line-clamp-2">{item.description}</div>
                    {item.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {item.tags.slice(0, 3).map(tag => (
                          <span key={tag} className="text-[8px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">
                            {tag}
                          </span>
                        ))}
                        {item.tags.length > 3 && (
                          <span className="text-[8px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#666]">
                            +{item.tags.length - 3}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {selectedItem && (
          <div className="w-64 border-l border-[#1e1e1e] overflow-y-auto p-3 bg-[#0a0a0a]">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-semibold text-[#ddd]">Details</span>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-[#666] hover:text-[#aaa] text-[10px]"
              >
                <i className="fa-solid fa-times" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <div className="text-[9px] text-[#666] mb-0.5">Name</div>
                <div className="text-[11px] text-[#ddd]">{selectedItem.name}</div>
              </div>

              <div>
                <div className="text-[9px] text-[#666] mb-0.5">Description</div>
                <div className="text-[10px] text-[#bbb]">{selectedItem.description}</div>
              </div>

              <div>
                <div className="text-[9px] text-[#666] mb-0.5">Category</div>
                <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ backgroundColor: `${CATEGORY_COLORS[selectedItem.category]}20`, color: CATEGORY_COLORS[selectedItem.category] }}>
                  {selectedItem.category}
                </span>
              </div>

              {selectedItem.tags.length > 0 && (
                <div>
                  <div className="text-[9px] text-[#666] mb-1">Tags</div>
                  <div className="flex flex-wrap gap-1">
                    {selectedItem.tags.map(tag => (
                      <span key={tag} className="text-[8px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#aaa]">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedItem.category === 'templates' && (
                <button
                  className="w-full mt-2 px-3 py-1.5 bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-lg text-[10px] font-semibold hover:opacity-90 transition-opacity"
                  onClick={() => {
                    const genre = selectedItem.id;
                    gameTemplateApi.scaffold('NewProject', genre);
                  }}
                >
                  <i className="fa-solid fa-download mr-1" />
                  Scaffold Project
                </button>
              )}

              {selectedItem.category === 'commands' && (
                <button
                  className="w-full mt-2 px-3 py-1.5 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-lg text-[10px] font-semibold hover:opacity-90 transition-opacity"
                  onClick={() => {
                    const slash = selectedItem.name;
                    studioCommandApi.execute(slash);
                  }}
                >
                  <i className="fa-solid fa-play mr-1" />
                  Execute Command
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AssetBrowser;
