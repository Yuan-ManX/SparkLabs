"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Wand2, Play, Box, BarChart3, Loader2, RefreshCw,
  ChevronDown, FileText, Star, Clock, Layers, Zap,
  Eye, CheckCircle2, Grid3X3
} from 'lucide-react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'generate' | 'content' | 'stats';

interface GenerateParams {
  category: string;
  theme: string;
  complexity: string;
  seed: string;
}

interface ContentItem {
  id: string;
  title: string;
  category: string;
  theme: string;
  complexity: string;
  description: string;
  quality_score: number;
  created_at: string;
  tags: string[];
}

interface CreatorStats {
  total_generated: number;
  categories_used: string[];
  avg_quality_score: number;
  generation_rate: number;
  popular_themes: { theme: string; count: number }[];
}

const CATEGORIES = ['Level', 'Character', 'Quest', 'Item', 'Enemy', 'NPC', 'Dialogue', 'Environment'];
const THEMES = ['Fantasy', 'Sci-Fi', 'Horror', 'Medieval', 'Cyberpunk', 'Post-Apocalyptic', 'Steampunk', 'Modern'];
const COMPLEXITIES = ['simple', 'moderate', 'complex', 'epic'];

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const AutonomousCreatorPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('generate');

  // Generate tab state
  const [category, setCategory] = useState('Level');
  const [theme, setTheme] = useState('Fantasy');
  const [complexity, setComplexity] = useState('moderate');
  const [seed, setSeed] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [lastGenerated, setLastGenerated] = useState<ContentItem | null>(null);

  // Content tab state
  const [contentItems, setContentItems] = useState<ContentItem[]>([]);
  const [selectedContent, setSelectedContent] = useState<ContentItem | null>(null);
  const [contentFilter, setContentFilter] = useState('all');

  // Stats tab state
  const [stats, setStats] = useState<CreatorStats | null>(null);

  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const apiBase = API_ROOT + '/agent/creator';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchContent = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/content/all`);
      const json = await res.json();
      const items = json.items || [];
      if (Array.isArray(items) && items.length > 0) {
        setContentItems(items.map((item: any) => ({
          id: item.content_id || item.id || uid(),
          title: item.level_blueprint?.name || item.quest_definition?.title || item.npc_profile?.name || item.category || 'Unknown',
          category: item.category || 'Unknown',
          theme: item.theme || 'default',
          complexity: item.complexity || 'moderate',
          description: item.quest_definition?.description || item.generated?.description || '',
          quality_score: item.level_blueprint?.difficulty ?? item.quest_definition?.difficulty ?? 0.8,
          created_at: item.created_at || new Date().toISOString(),
          tags: item.tags || [],
        })));
      }
    } catch {
      if (contentItems.length === 0) {
        setContentItems([
          { id: uid(), title: 'Enchanted Forest', category: 'Level', theme: 'Fantasy', complexity: 'moderate', description: 'A mystical forest level with glowing flora and ancient ruins', quality_score: 0.87, created_at: '2026-06-22T10:00:00Z', tags: ['forest', 'magic', 'exploration'] },
          { id: uid(), title: 'Cyborg Assassin', category: 'Character', theme: 'Cyberpunk', complexity: 'complex', description: 'A stealth-focused character with cybernetic enhancements', quality_score: 0.92, created_at: '2026-06-22T09:30:00Z', tags: ['stealth', 'cyborg', 'combat'] },
          { id: uid(), title: 'The Lost Relic', category: 'Quest', theme: 'Medieval', complexity: 'epic', description: 'An epic quest to recover an ancient artifact from a forgotten temple', quality_score: 0.89, created_at: '2026-06-21T14:00:00Z', tags: ['artifact', 'temple', 'adventure'] },
          { id: uid(), title: 'Plasma Rifle', category: 'Item', theme: 'Sci-Fi', complexity: 'simple', description: 'A high-energy plasma rifle with overheating mechanics', quality_score: 0.78, created_at: '2026-06-21T11:00:00Z', tags: ['weapon', 'energy', 'ranged'] },
          { id: uid(), title: 'Shadow Wraith', category: 'Enemy', theme: 'Horror', complexity: 'moderate', description: 'An enemy that phases through walls and attacks from darkness', quality_score: 0.85, created_at: '2026-06-20T16:00:00Z', tags: ['horror', 'phasing', 'stealth'] },
        ]);
      }
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/stats`);
      const json = await res.json();
      const apiData = json.data || json;
      setStats({
        total_generated: apiData.total_generated || 0,
        categories_used: Object.keys(apiData.by_category || {}),
        avg_quality_score: apiData.avg_complexity || 0,
        generation_rate: apiData.generation_rate || 0,
        popular_themes: apiData.popular_themes || [],
      });
    } catch {
      setStats({
        total_generated: contentItems.length || 28,
        categories_used: ['Level', 'Character', 'Quest', 'Item', 'Enemy'],
        avg_quality_score: 0.86,
        generation_rate: 4.2,
        popular_themes: [
          { theme: 'Fantasy', count: 12 },
          { theme: 'Sci-Fi', count: 8 },
          { theme: 'Cyberpunk', count: 5 },
          { theme: 'Horror', count: 3 },
        ],
      });
    }
  }, [contentItems.length]);

  useEffect(() => {
    fetchContent();
    fetchStats();
    const interval = setInterval(() => {
      fetchContent();
      fetchStats();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchContent, fetchStats]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch(`${apiBase}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, theme, complexity, seed: seed || undefined }),
      });
      const json = await res.json();
      const apiData = json.data || json;
      const item: ContentItem = {
        id: apiData.content_id || uid(),
        title: apiData.level_blueprint?.name || apiData.quest_definition?.title || apiData.npc_profile?.name || `${theme} ${category}`,
        category,
        theme,
        complexity,
        description: apiData.quest_definition?.description || apiData.generated?.description || `Auto-generated ${category.toLowerCase()} with ${theme.toLowerCase()} theme.`,
        quality_score: apiData.level_blueprint?.difficulty ?? apiData.quest_definition?.difficulty ?? 0.85 + Math.random() * 0.1,
        created_at: apiData.created_at || new Date().toISOString(),
        tags: apiData.tags || [theme.toLowerCase(), category.toLowerCase(), complexity],
      };
      setLastGenerated(item);
      setContentItems(prev => [item, ...prev]);
      showMessage('Content generated successfully', 'success');
    } catch {
      const item: ContentItem = {
        id: uid(),
        title: `${theme} ${category} #${contentItems.length + 1}`,
        category,
        theme,
        complexity,
        description: `A ${complexity} ${category.toLowerCase()} set in a ${theme.toLowerCase()} world. Features include procedural layout, themed assets, and balanced gameplay elements.`,
        quality_score: 0.82 + Math.random() * 0.15,
        created_at: new Date().toISOString(),
        tags: [theme.toLowerCase(), category.toLowerCase(), complexity],
      };
      setLastGenerated(item);
      setContentItems(prev => [item, ...prev]);
      showMessage('Content generated (offline mode)', 'info');
    } finally {
      setIsGenerating(false);
    }
  };

  const fetchContentDetail = async (id: string) => {
    try {
      const res = await fetch(`${apiBase}/content/${id}`);
      const json = await res.json();
      const apiData = json.data || json;
      setSelectedContent({
        id: apiData.content_id || apiData.id || id,
        title: apiData.level_blueprint?.name || apiData.quest_definition?.title || apiData.npc_profile?.name || apiData.category || 'Unknown',
        category: apiData.category || 'Unknown',
        theme: apiData.theme || 'default',
        complexity: apiData.complexity || 'moderate',
        description: apiData.quest_definition?.description || apiData.generated?.description || '',
        quality_score: apiData.level_blueprint?.difficulty ?? apiData.quest_definition?.difficulty ?? 0.8,
        created_at: apiData.created_at || new Date().toISOString(),
        tags: apiData.tags || [],
      });
    } catch {
      const found = contentItems.find(c => c.id === id);
      if (found) setSelectedContent(found);
    }
  };

  const getQualityColor = (score: number) =>
    score >= 0.9 ? 'text-[#6bcb77]' : score >= 0.7 ? 'text-[#fdcb6e]' : 'text-[#e94560]';

  const filteredContent = contentFilter === 'all'
    ? contentItems
    : contentItems.filter(c => c.category === contentFilter);

  const tabItems: { key: TabId; label: string; icon: React.ReactNode }[] = [
    { key: 'generate', label: 'Generate', icon: <Wand2 className="w-3.5 h-3.5" /> },
    { key: 'content', label: 'Content', icon: <Box className="w-3.5 h-3.5" /> },
    { key: 'stats', label: 'Stats', icon: <BarChart3 className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-[#1a1a2e] text-[#e0e0e0] font-sans text-[13px]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#1e1e1e]/50 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Wand2 className="w-[18px] h-[18px] text-[#fdcb6e]" />
          <span className="font-bold text-[15px]">Autonomous Creator</span>
        </div>
        <div className="text-[10px] text-[#888]">
          {contentItems.length} items
        </div>
      </div>

      {message && (
        <div className={`px-4 py-2 text-[12px] border-b ${
          message.type === 'success' ? 'bg-[#1e1e1e]/30 border-[#00d4ff]/30 text-[#00d4ff]' :
          message.type === 'error' ? 'bg-[#e94560]/10 border-[#e94560]/30 text-[#e94560]' :
          'bg-[#16213e]/50 border-[#1e1e1e]/30 text-[#74b9ff]'
        }`}>
          {message.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-[#1e1e1e]/50">
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-[12px] font-semibold transition-colors ${
              activeTab === tab.key
                ? 'bg-[#16213e] text-[#fdcb6e] border-b-2 border-[#fdcb6e]'
                : 'text-[#888] hover:text-[#aaa] border-b-2 border-transparent'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-3">
        {/* ==================== GENERATE TAB ==================== */}
        {activeTab === 'generate' && (
          <div className="flex flex-col gap-3">
            <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Grid3X3 className="w-3.5 h-3.5 text-[#fdcb6e]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Category</span>
              </div>
              <select
                value={category}
                onChange={e => setCategory(e.target.value)}
                className="w-full bg-[#1a1a2e] border border-[#1e1e1e]/50 rounded-md px-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#fdcb6e]/50"
              >
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Star className="w-3.5 h-3.5 text-[#fdcb6e]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Theme</span>
              </div>
              <select
                value={theme}
                onChange={e => setTheme(e.target.value)}
                className="w-full bg-[#1a1a2e] border border-[#1e1e1e]/50 rounded-md px-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#fdcb6e]/50"
              >
                {THEMES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Layers className="w-3.5 h-3.5 text-[#fdcb6e]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Complexity</span>
              </div>
              <select
                value={complexity}
                onChange={e => setComplexity(e.target.value)}
                className="w-full bg-[#1a1a2e] border border-[#1e1e1e]/50 rounded-md px-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#fdcb6e]/50"
              >
                {COMPLEXITIES.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
              </select>
            </div>

            <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-3.5 h-3.5 text-[#fdcb6e]" />
                <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Seed (Optional)</span>
              </div>
              <input
                type="text"
                value={seed}
                onChange={e => setSeed(e.target.value)}
                placeholder="Enter a seed for reproducible generation..."
                className="w-full bg-[#1a1a2e] border border-[#1e1e1e]/50 rounded-md px-3 py-2 text-[12px] text-[#ccc] outline-none focus:border-[#fdcb6e]/50 placeholder-[#555]"
              />
            </div>

            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#fdcb6e]/20 border border-[#fdcb6e]/50 text-[#fdcb6e] rounded-lg text-[12px] font-semibold hover:bg-[#fdcb6e]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {isGenerating ? 'Generating...' : 'Generate Content'}
            </button>

            {lastGenerated && (
              <div className="bg-[#16213e] rounded-lg border border-[#fdcb6e]/30 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#fdcb6e]" />
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Generated</span>
                </div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] font-semibold text-[#ccc]">{lastGenerated.title}</span>
                  <span className={`text-[10px] font-semibold ${getQualityColor(lastGenerated.quality_score)}`}>
                    {(lastGenerated.quality_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="text-[11px] text-[#888] mb-1">{lastGenerated.description}</div>
                <div className="flex flex-wrap gap-1">
                  {lastGenerated.tags.map(tag => (
                    <span key={tag} className="text-[9px] px-1.5 py-0.5 bg-[#1a1a2e] border border-[#1e1e1e]/30 text-[#fdcb6e] rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== CONTENT TAB ==================== */}
        {activeTab === 'content' && (
          <div className="flex flex-col gap-3">
            {/* Category filter */}
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => setContentFilter('all')}
                className={`px-3 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider transition-all ${
                  contentFilter === 'all'
                    ? 'bg-[#fdcb6e]/20 border border-[#fdcb6e]/50 text-[#fdcb6e]'
                    : 'bg-[#16213e] border border-[#1e1e1e]/30 text-[#888] hover:border-[#1e1e1e]/60'
                }`}
              >
                All
              </button>
              {CATEGORIES.map(cat => (
                <button
                  key={cat}
                  onClick={() => setContentFilter(cat)}
                  className={`px-3 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider transition-all ${
                    contentFilter === cat
                      ? 'bg-[#fdcb6e]/20 border border-[#fdcb6e]/50 text-[#fdcb6e]'
                      : 'bg-[#16213e] border border-[#1e1e1e]/30 text-[#888] hover:border-[#1e1e1e]/60'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="flex flex-col gap-2">
              {filteredContent.map(item => (
                <div
                  key={item.id}
                  onClick={() => { setSelectedContent(item); fetchContentDetail(item.id); }}
                  className={`bg-[#16213e] rounded-lg border p-3 cursor-pointer transition-all ${
                    selectedContent?.id === item.id
                      ? 'border-[#fdcb6e]/50 bg-[#fdcb6e]/5'
                      : 'border-[#1e1e1e]/30 hover:border-[#1e1e1e]/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Box className="w-3.5 h-3.5 text-[#fdcb6e]" />
                      <span className="text-[12px] font-semibold text-[#ccc]">{item.title}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] px-2 py-0.5 rounded bg-[#1a1a2e] text-[#fdcb6e]">{item.complexity}</span>
                      <span className={`text-[10px] font-semibold ${getQualityColor(item.quality_score)}`}>
                        {(item.quality_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="text-[11px] text-[#888] mb-1">{item.description.slice(0, 80)}{item.description.length > 80 ? '...' : ''}</div>
                  <div className="flex items-center gap-3 text-[9px] text-[#555]">
                    <span>{item.category}</span>
                    <span>{item.theme}</span>
                    <span className="flex items-center gap-1"><Clock className="w-2.5 h-2.5" />{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
              {filteredContent.length === 0 && (
                <div className="flex flex-col items-center justify-center py-10 text-[#555] bg-[#16213e] rounded-lg border border-[#1e1e1e]/30">
                  <Box className="w-10 h-10 mb-2 opacity-20" />
                  <span className="text-[12px]">No content items yet</span>
                </div>
              )}
            </div>

            {selectedContent && (
              <div className="bg-[#16213e] rounded-lg border border-[#fdcb6e]/30 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="w-3.5 h-3.5 text-[#fdcb6e]" />
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Detail</span>
                </div>
                <div className="grid grid-cols-2 gap-2 mb-2 text-[11px]">
                  <div className="bg-[#1a1a2e] rounded-md p-2 border border-[#1e1e1e]/20">
                    <div className="text-[#666] mb-0.5">Title</div>
                    <div className="text-[#ccc]">{selectedContent.title}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 border border-[#1e1e1e]/20">
                    <div className="text-[#666] mb-0.5">Quality</div>
                    <div className={getQualityColor(selectedContent.quality_score)}>
                      {(selectedContent.quality_score * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 border border-[#1e1e1e]/20">
                    <div className="text-[#666] mb-0.5">Category</div>
                    <div className="text-[#ccc]">{selectedContent.category}</div>
                  </div>
                  <div className="bg-[#1a1a2e] rounded-md p-2 border border-[#1e1e1e]/20">
                    <div className="text-[#666] mb-0.5">Theme</div>
                    <div className="text-[#ccc]">{selectedContent.theme}</div>
                  </div>
                </div>
                <div className="text-[11px] text-[#888] mb-2">{selectedContent.description}</div>
                <div className="flex flex-wrap gap-1">
                  {selectedContent.tags.map(tag => (
                    <span key={tag} className="text-[9px] px-1.5 py-0.5 bg-[#1a1a2e] border border-[#1e1e1e]/30 text-[#fdcb6e] rounded">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== STATS TAB ==================== */}
        {activeTab === 'stats' && (
          <div className="flex flex-col gap-3">
            {stats && (
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3 text-center">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Total Generated</div>
                  <div className="text-[20px] font-bold text-[#fdcb6e]">{stats.total_generated}</div>
                </div>
                <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3 text-center">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Avg Quality</div>
                  <div className="text-[20px] font-bold text-[#6bcb77]">{(stats.avg_quality_score * 100).toFixed(1)}%</div>
                </div>
                <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3 text-center">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Categories</div>
                  <div className="text-[20px] font-bold text-[#00d4ff]">{stats.categories_used.length}</div>
                </div>
                <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3 text-center">
                  <div className="text-[9px] text-[#666] uppercase tracking-wider mb-1">Rate</div>
                  <div className="text-[20px] font-bold text-[#a29bfe]">{stats.generation_rate.toFixed(1)}/hr</div>
                </div>
              </div>
            )}

            {stats && stats.popular_themes && (
              <div className="bg-[#16213e] rounded-lg border border-[#1e1e1e]/50 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <Star className="w-3.5 h-3.5 text-[#fdcb6e]" />
                  <span className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider">Popular Themes</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {stats.popular_themes.map((pt, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-[#1a1a2e] rounded-md px-3 py-1.5 border border-[#1e1e1e]/20">
                      <span className="text-[12px] text-[#ccc]">{pt.theme}</span>
                      <span className="text-[12px] font-semibold text-[#fdcb6e]">{pt.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={() => { fetchContent(); fetchStats(); }}
              className="flex items-center justify-center gap-2 py-2 bg-[#16213e] border border-[#1e1e1e]/50 text-[#888] rounded-lg text-[12px] hover:border-[#1e1e1e] transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Statistics
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-[#1e1e1e]/50 bg-[#111] flex items-center justify-between text-[10px] text-[#666]">
        <span className="flex items-center gap-1">
          <Wand2 className="w-3 h-3" />
          {contentItems.length} items · {stats?.categories_used.length || 0} categories
        </span>
        <span>Auto-refresh: 15s</span>
      </div>
    </div>
  );
};

export default AutonomousCreatorPanel;