import React, { useState, useCallback, useRef, useEffect } from 'react';

type LocaleCode = 'en' | 'zh' | 'ja' | 'ko' | 'fr' | 'de' | 'es' | 'pt' | 'ru' | 'ar';
type Category = 'ui' | 'dialogue' | 'system' | 'items' | 'quests' | 'achievements';

interface LocaleMeta {
  code: LocaleCode;
  label: string;
  flag: string;
}

interface LocalizationEntry {
  id: string;
  key: string;
  sourceText: string;
  category: Category;
  translations: Partial<Record<LocaleCode, string>>;
}

interface AddKeyForm {
  key: string;
  sourceText: string;
  category: Category;
}

const LOCALES: LocaleMeta[] = [
  { code: 'en', label: 'English', flag: 'US' },
  { code: 'zh', label: 'Chinese', flag: 'CN' },
  { code: 'ja', label: 'Japanese', flag: 'JP' },
  { code: 'ko', label: 'Korean', flag: 'KR' },
  { code: 'fr', label: 'French', flag: 'FR' },
  { code: 'de', label: 'German', flag: 'DE' },
  { code: 'es', label: 'Spanish', flag: 'ES' },
  { code: 'pt', label: 'Portuguese', flag: 'PT' },
  { code: 'ru', label: 'Russian', flag: 'RU' },
  { code: 'ar', label: 'Arabic', flag: 'SA' },
];

const CATEGORIES: { value: Category; label: string; color: string }[] = [
  { value: 'ui', label: 'UI', color: '#22c55e' },
  { value: 'dialogue', label: 'Dialogue', color: '#3b82f6' },
  { value: 'system', label: 'System', color: '#8b5cf6' },
  { value: 'items', label: 'Items', color: '#f59e0b' },
  { value: 'quests', label: 'Quests', color: '#f97316' },
  { value: 'achievements', label: 'Achievements', color: '#ec4899' },
];

const SEED_ENTRIES: LocalizationEntry[] = [
  { id: 'l1', key: 'ui.main_menu.play', sourceText: 'Play', category: 'ui', translations: { zh: '开始游戏', ja: 'プレイ', ko: '플레이', fr: 'Jouer', de: 'Spielen', es: 'Jugar', pt: 'Jogar', ru: 'Играть', ar: 'لعب' } },
  { id: 'l2', key: 'ui.main_menu.settings', sourceText: 'Settings', category: 'ui', translations: { zh: '设置', ja: '設定', ko: '설정' } },
  { id: 'l3', key: 'ui.main_menu.quit', sourceText: 'Quit', category: 'ui', translations: { zh: '退出', ja: '終了' } },
  { id: 'l4', key: 'ui.inventory.title', sourceText: 'Inventory', category: 'ui', translations: { zh: '背包', ja: 'インベントリ' } },
  { id: 'l5', key: 'ui.inventory.empty', sourceText: 'No items in inventory', category: 'ui', translations: { zh: '背包是空的' } },
  { id: 'l6', key: 'dialogue.greeting.merchant', sourceText: 'Welcome, traveler! What can I get for you?', category: 'dialogue', translations: { zh: '欢迎，旅行者！你想要什么？', ja: 'ようこそ、旅人よ！何をお求めですか？' } },
  { id: 'l7', key: 'dialogue.greeting.guard', sourceText: 'Halt! Who goes there?', category: 'dialogue', translations: {} },
  { id: 'l8', key: 'dialogue.farewell.npc', sourceText: 'Safe travels, friend.', category: 'dialogue', translations: { zh: '一路平安，朋友。', ja: '良い旅を、友よ。' } },
  { id: 'l9', key: 'system.error.save_failed', sourceText: 'Failed to save game progress.', category: 'system', translations: { zh: '保存游戏进度失败。', ja: 'ゲームの進行状況の保存に失敗しました。' } },
  { id: 'l10', key: 'system.error.network', sourceText: 'Network connection lost. Retrying...', category: 'system', translations: { zh: '网络连接丢失。正在重试...' } },
  { id: 'l11', key: 'system.notify.autosave', sourceText: 'Game auto-saved successfully.', category: 'system', translations: { zh: '游戏已自动保存。' } },
  { id: 'l12', key: 'items.sword.iron.name', sourceText: 'Iron Sword', category: 'items', translations: { zh: '铁剑', ja: '鉄の剣' } },
  { id: 'l13', key: 'items.sword.iron.desc', sourceText: 'A sturdy iron blade, forged by skilled hands.', category: 'items', translations: { zh: '一把坚固的铁剑，由巧匠锻造。' } },
  { id: 'l14', key: 'items.potion.health.name', sourceText: 'Health Potion', category: 'items', translations: { zh: '生命药水', ja: '回復ポーション' } },
  { id: 'l15', key: 'items.potion.health.desc', sourceText: 'Restores 50 HP over 5 seconds.', category: 'items', translations: { zh: '在5秒内恢复50点生命值。' } },
  { id: 'l16', key: 'quests.main.find_artifact.title', sourceText: 'Find the Lost Artifact', category: 'quests', translations: { zh: '寻找失落的遗物', ja: '失われた遺物を探せ' } },
  { id: 'l17', key: 'quests.main.find_artifact.desc', sourceText: 'The village elder has asked you to recover an ancient artifact from the Dark Forest.', category: 'quests', translations: { zh: '村长请你从黑暗森林中找回一件古代遗物。' } },
  { id: 'l18', key: 'quests.side.herb_collection.title', sourceText: 'Herb Collection', category: 'quests', translations: { zh: '采集草药' } },
  { id: 'l19', key: 'achievements.first_kill.title', sourceText: 'First Blood', category: 'achievements', translations: { zh: '第一滴血', ja: 'ファーストブラッド' } },
  { id: 'l20', key: 'achievements.first_kill.desc', sourceText: 'Defeat your first enemy.', category: 'achievements', translations: { zh: '击败你的第一个敌人。' } },
  { id: 'l21', key: 'achievements.treasure_hunter.title', sourceText: 'Treasure Hunter', category: 'achievements', translations: { zh: '寻宝猎人' } },
  { id: 'l22', key: 'achievements.treasure_hunter.desc', sourceText: 'Open 50 treasure chests.', category: 'achievements', translations: {} },
  { id: 'l23', key: 'ui.shop.buy', sourceText: 'Buy', category: 'ui', translations: {} },
  { id: 'l24', key: 'ui.shop.sell', sourceText: 'Sell', category: 'ui', translations: { zh: '出售' } },
  { id: 'l25', key: 'dialogue.quest.accept', sourceText: 'I will help you with this task.', category: 'dialogue', translations: {} },
];

const emptyForm: AddKeyForm = { key: '', sourceText: '', category: 'ui' };

const LocalizationEditor: React.FC = () => {
  const [entries, setEntries] = useState<LocalizationEntry[]>(SEED_ENTRIES);
  const [selectedLocale, setSelectedLocale] = useState<LocaleCode>('zh');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<Category | 'all'>('all');
  const [editingEntryId, setEditingEntryId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [addForm, setAddForm] = useState<AddKeyForm>(emptyForm);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingEntryId && editInputRef.current) {
      editInputRef.current.focus();
    }
  }, [editingEntryId]);

  const filteredEntries = entries.filter((entry) => {
    if (categoryFilter !== 'all' && entry.category !== categoryFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        entry.key.toLowerCase().includes(q) ||
        entry.sourceText.toLowerCase().includes(q) ||
        (entry.translations[selectedLocale] || '').toLowerCase().includes(q)
      );
    }
    return true;
  });

  const stats = (() => {
    const total = entries.length;
    const translated = entries.filter((e) => {
      const val = e.translations[selectedLocale];
      return val && val.trim().length > 0;
    }).length;
    const missing = total - translated;
    const percentage = total > 0 ? Math.round((translated / total) * 100) : 0;
    return { total, translated, missing, percentage };
  })();

  const selectedLocaleMeta = LOCALES.find((l) => l.code === selectedLocale) || LOCALES[0];

  const handleEditStart = useCallback(
    (entryId: string) => {
      const entry = entries.find((e) => e.id === entryId);
      if (!entry) return;
      setEditingEntryId(entryId);
      setEditingValue(entry.translations[selectedLocale] || '');
    },
    [entries, selectedLocale]
  );

  const handleEditSave = useCallback(
    (entryId: string) => {
      setEntries((prev) =>
        prev.map((e) => {
          if (e.id !== entryId) return e;
          return {
            ...e,
            translations: {
              ...e.translations,
              [selectedLocale]: editingValue.trim() || undefined,
            },
          };
        })
      );
      setEditingEntryId(null);
      setEditingValue('');
    },
    [editingValue, selectedLocale]
  );

  const handleEditCancel = useCallback(() => {
    setEditingEntryId(null);
    setEditingValue('');
  }, []);

  const handleEditKeyDown = useCallback(
    (e: React.KeyboardEvent, entryId: string) => {
      if (e.key === 'Enter') handleEditSave(entryId);
      if (e.key === 'Escape') handleEditCancel();
    },
    [handleEditSave, handleEditCancel]
  );

  const handleAddEntry = useCallback(() => {
    if (!addForm.key.trim() || !addForm.sourceText.trim()) return;
    const newEntry: LocalizationEntry = {
      id: `l_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      key: addForm.key.trim(),
      sourceText: addForm.sourceText.trim(),
      category: addForm.category,
      translations: {},
    };
    setEntries((prev) => [...prev, newEntry]);
    setAddForm(emptyForm);
    setShowAddDialog(false);
  }, [addForm]);

  const handleDeleteEntry = useCallback((entryId: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== entryId));
    if (editingEntryId === entryId) {
      setEditingEntryId(null);
      setEditingValue('');
    }
  }, [editingEntryId]);

  const handleExport = useCallback(() => {
    const exportData = {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      locales: LOCALES.map((l) => ({ code: l.code, label: l.label })),
      entries: entries.map((e) => ({
        key: e.key,
        sourceText: e.sourceText,
        category: e.category,
        translations: e.translations,
      })),
    };
    const json = JSON.stringify(exportData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `localization_${selectedLocale}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [entries, selectedLocale]);

  const handleImport = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const data = JSON.parse(ev.target?.result as string);
          if (data.entries && Array.isArray(data.entries)) {
            const imported: LocalizationEntry[] = data.entries.map(
              (item: any, idx: number) => ({
                id: `l_import_${Date.now()}_${idx}`,
                key: item.key || '',
                sourceText: item.sourceText || '',
                category: (item.category as Category) || 'ui',
                translations: item.translations || {},
              })
            );
            setEntries((prev) => [...prev, ...imported]);
          }
        } catch {
          // ignore invalid JSON
        }
      };
      reader.readAsText(file);
      e.target.value = '';
    },
    []
  );

  const updateAddForm = useCallback(
    <K extends keyof AddKeyForm>(field: K, value: AddKeyForm[K]) => {
      setAddForm((prev) => ({ ...prev, [field]: value }));
    },
    []
  );

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <h3 style={{ margin: 0, color: '#06b6d4' }}>Localization Editor</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={handleImport}
            style={{
              padding: '5px 12px', borderRadius: 6, fontSize: 11, border: '1px solid #444',
              background: '#1a1a2e', color: '#aaa', cursor: 'pointer',
            }}
          >
            Import JSON
          </button>
          <input ref={fileInputRef} type="file" accept=".json" onChange={handleFileChange} style={{ display: 'none' }} />
          <button
            onClick={handleExport}
            style={{
              padding: '5px 12px', borderRadius: 6, fontSize: 11, border: '1px solid #444',
              background: '#1a1a2e', color: '#aaa', cursor: 'pointer',
            }}
          >
            Export JSON
          </button>
          <button
            onClick={() => setShowAddDialog(true)}
            style={{
              padding: '5px 12px', borderRadius: 6, fontSize: 11, border: '1px solid #06b6d4',
              background: '#0d3b4e', color: '#06b6d4', cursor: 'pointer',
            }}
          >
            + Add Key
          </button>
        </div>
      </div>

      {/* Stats panel */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        {[
          { label: 'Total Keys', value: stats.total, color: '#e0e0e0' },
          { label: 'Translated', value: stats.translated, color: '#22c55e' },
          { label: 'Missing', value: stats.missing, color: '#ef4444' },
        ].map((stat) => (
          <div key={stat.label} style={{ background: '#1a1a2e', padding: '8px 14px', borderRadius: 6, minWidth: 70 }}>
            <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>{stat.label}</div>
            <div style={{ fontSize: 20, fontWeight: 'bold', color: stat.color }}>{stat.value}</div>
          </div>
        ))}
        <div style={{ background: '#1a1a2e', padding: '8px 14px', borderRadius: 6, minWidth: 80, flex: 1 }}>
          <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Completion</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 8, background: '#333', borderRadius: 4, overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%', borderRadius: 4,
                  background: stats.percentage >= 100 ? '#22c55e' : stats.percentage >= 50 ? '#f59e0b' : '#ef4444',
                  width: `${stats.percentage}%`,
                  transition: 'width 0.3s',
                }}
              />
            </div>
            <span style={{ fontSize: 13, fontWeight: 'bold', color: '#e0e0e0' }}>{stats.percentage}%</span>
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        {/* Search */}
        <div style={{ position: 'relative', flex: '1 1 200px', maxWidth: 320 }}>
          <input
            type="text"
            placeholder="Search keys..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%', padding: '6px 10px 6px 32px', borderRadius: 6, fontSize: 12,
              background: '#1a1a2e', border: '1px solid #333', color: '#e0e0e0', outline: 'none',
              fontFamily: 'monospace',
            }}
          />
          <span style={{ position: 'absolute', left: 10, top: 7, fontSize: 12, color: '#666' }}>&#128269;</span>
        </div>

        {/* Locale selector */}
        <select
          value={selectedLocale}
          onChange={(e) => setSelectedLocale(e.target.value as LocaleCode)}
          style={{
            padding: '6px 10px', borderRadius: 6, fontSize: 12,
            background: '#1a1a2e', border: '1px solid #333', color: '#e0e0e0',
            fontFamily: 'monospace', cursor: 'pointer', outline: 'none',
          }}
        >
          {LOCALES.map((loc) => (
            <option key={loc.code} value={loc.code}>
              {loc.label}
            </option>
          ))}
        </select>

        {/* Category filter */}
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            onClick={() => setCategoryFilter('all')}
            style={{
              padding: '4px 10px', borderRadius: 6, fontSize: 11,
              border: categoryFilter === 'all' ? '2px solid #aaa' : '1px solid #333',
              background: categoryFilter === 'all' ? '#2a2a2a' : '#1a1a2e',
              color: categoryFilter === 'all' ? '#e0e0e0' : '#888',
              cursor: 'pointer',
            }}
          >
            All
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setCategoryFilter(cat.value)}
              style={{
                padding: '4px 10px', borderRadius: 6, fontSize: 11,
                border: categoryFilter === cat.value ? `2px solid ${cat.color}` : '1px solid #333',
                background: categoryFilter === cat.value ? `${cat.color}22` : '#1a1a2e',
                color: categoryFilter === cat.value ? cat.color : '#888',
                cursor: 'pointer',
              }}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={{ background: '#0a0a0a', borderRadius: 8, border: '1px solid #2a2a2a', overflow: 'hidden' }}>
        {/* Table header */}
        <div
          style={{
            display: 'flex', padding: '8px 12px', background: '#111', borderBottom: '1px solid #2a2a2a',
            fontSize: 11, color: '#888', fontWeight: 'bold', textTransform: 'uppercase',
          }}
        >
          <div style={{ width: 80 }}>Category</div>
          <div style={{ flex: '0 0 240px', minWidth: 0 }}>Key</div>
          <div style={{ flex: '0 0 320px', minWidth: 0 }}>Source (English)</div>
          <div style={{ flex: 1, minWidth: 0 }}>Target ({selectedLocaleMeta.label})</div>
          <div style={{ width: 40 }} />
        </div>

        {/* Table body */}
        <div style={{ maxHeight: 'calc(100vh - 380px)', overflow: 'auto' }}>
          {filteredEntries.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: '#666', fontSize: 12 }}>
              No localization entries found.
            </div>
          ) : (
            filteredEntries.map((entry) => {
              const catMeta = CATEGORIES.find((c) => c.value === entry.category);
              const isEditing = editingEntryId === entry.id;
              return (
                <div
                  key={entry.id}
                  style={{
                    display: 'flex', padding: '6px 12px', borderBottom: '1px solid #1a1a1a',
                    fontSize: 12, alignItems: 'center',
                    background: isEditing ? '#0d1a2a' : 'transparent',
                    transition: 'background 0.15s',
                  }}
                >
                  {/* Category badge */}
                  <div style={{ width: 80 }}>
                    <span
                      style={{
                        padding: '1px 6px', borderRadius: 3, fontSize: 10,
                        background: (catMeta?.color || '#666') + '33',
                        color: catMeta?.color || '#666',
                        fontWeight: 'bold',
                      }}
                    >
                      {catMeta?.label || entry.category}
                    </span>
                  </div>

                  {/* Key */}
                  <div style={{ flex: '0 0 240px', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#aaa', paddingRight: 8 }}>
                    {entry.key}
                  </div>

                  {/* Source (English) */}
                  <div style={{ flex: '0 0 320px', minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#e0e0e0', paddingRight: 8 }}>
                    {entry.sourceText}
                  </div>

                  {/* Target translation */}
                  <div
                    style={{ flex: 1, minWidth: 0, cursor: isEditing ? 'default' : 'pointer', paddingRight: 8 }}
                    onClick={() => !isEditing && handleEditStart(entry.id)}
                  >
                    {isEditing ? (
                      <input
                        ref={editInputRef}
                        type="text"
                        value={editingValue}
                        onChange={(e) => setEditingValue(e.target.value)}
                        onBlur={() => handleEditSave(entry.id)}
                        onKeyDown={(e) => handleEditKeyDown(e, entry.id)}
                        placeholder="Enter translation..."
                        style={{
                          width: '100%', padding: '4px 8px', borderRadius: 4, fontSize: 12,
                          background: '#0a1a2e', border: '1px solid #3b82f6', color: '#e0e0e0',
                          outline: 'none', fontFamily: 'monospace',
                        }}
                      />
                    ) : (
                      <span style={{ color: entry.translations[selectedLocale] ? '#e0e0e0' : '#555', fontStyle: entry.translations[selectedLocale] ? 'normal' : 'italic' }}>
                        {entry.translations[selectedLocale] || '(empty)'}
                      </span>
                    )}
                  </div>

                  {/* Delete button */}
                  <div style={{ width: 40, textAlign: 'center' }}>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteEntry(entry.id); }}
                      title="Delete entry"
                      style={{
                        padding: '2px 6px', borderRadius: 4, fontSize: 14, border: 'none',
                        background: 'transparent', color: '#555', cursor: 'pointer',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = '#555')}
                    >
                      &#10005;
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Results count */}
      <div style={{ marginTop: 8, fontSize: 10, color: '#666' }}>
        Showing {filteredEntries.length} of {entries.length} entries
      </div>

      {/* Add Key Dialog */}
      {showAddDialog && (
        <>
          <div
            onClick={() => setShowAddDialog(false)}
            style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(0,0,0,0.6)', zIndex: 1000,
            }}
          />
          <div
            style={{
              position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
              zIndex: 1001, width: 420, background: '#141414', borderRadius: 10,
              border: '1px solid #2a2a2a', padding: 20,
            }}
          >
            <h4 style={{ margin: '0 0 16px', color: '#06b6d4', fontSize: 14 }}>Add Localization Key</h4>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>Key</label>
              <input
                type="text"
                placeholder="e.g. ui.main_menu.start"
                value={addForm.key}
                onChange={(e) => updateAddForm('key', e.target.value)}
                style={{
                  width: '100%', padding: '6px 10px', borderRadius: 6, fontSize: 12,
                  background: '#1a1a2e', border: '1px solid #333', color: '#e0e0e0',
                  outline: 'none', fontFamily: 'monospace', boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>Source Text (English)</label>
              <input
                type="text"
                placeholder="English text..."
                value={addForm.sourceText}
                onChange={(e) => updateAddForm('sourceText', e.target.value)}
                style={{
                  width: '100%', padding: '6px 10px', borderRadius: 6, fontSize: 12,
                  background: '#1a1a2e', border: '1px solid #333', color: '#e0e0e0',
                  outline: 'none', fontFamily: 'monospace', boxSizing: 'border-box',
                }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 11, color: '#888', marginBottom: 4 }}>Category</label>
              <select
                value={addForm.category}
                onChange={(e) => updateAddForm('category', e.target.value as Category)}
                style={{
                  width: '100%', padding: '6px 10px', borderRadius: 6, fontSize: 12,
                  background: '#1a1a2e', border: '1px solid #333', color: '#e0e0e0',
                  fontFamily: 'monospace', cursor: 'pointer', outline: 'none',
                }}
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button
                onClick={() => { setShowAddDialog(false); setAddForm(emptyForm); }}
                style={{
                  padding: '6px 14px', borderRadius: 6, fontSize: 12, border: '1px solid #444',
                  background: '#1a1a2e', color: '#aaa', cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleAddEntry}
                disabled={!addForm.key.trim() || !addForm.sourceText.trim()}
                style={{
                  padding: '6px 14px', borderRadius: 6, fontSize: 12, border: '1px solid #06b6d4',
                  background: (addForm.key.trim() && addForm.sourceText.trim()) ? '#0d3b4e' : '#1a1a2e',
                  color: (addForm.key.trim() && addForm.sourceText.trim()) ? '#06b6d4' : '#555',
                  cursor: (addForm.key.trim() && addForm.sourceText.trim()) ? 'pointer' : 'not-allowed',
                  opacity: (addForm.key.trim() && addForm.sourceText.trim()) ? 1 : 0.5,
                }}
              >
                Add Key
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default LocalizationEditor;