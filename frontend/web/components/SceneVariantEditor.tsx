import React, { useState, useCallback, useEffect } from 'react';

interface SceneVariant {
  variant_id: string;
  name: string;
  variant_type: 'BASE' | 'INHERITED' | 'OVERRIDE' | 'EXPERIMENTAL' | 'PUBLISHED';
  parent_id: string | null;
  scene_data: Record<string, unknown>;
  overrides: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface VariantStats {
  total: number;
  by_type: Record<string, number>;
}

interface DiffResult {
  added: Record<string, unknown>;
  removed: Record<string, unknown>;
  changed: Record<string, { old: unknown; new: unknown }>;
}

const API_BASE = 'http://localhost:8000/api/engine/scene-variant';

const TYPE_COLORS: Record<string, string> = {
  BASE: '#89b4fa',
  INHERITED: '#a6e3a1',
  OVERRIDE: '#f9e2af',
  EXPERIMENTAL: '#cba6f7',
  PUBLISHED: '#f5c266',
};

const TYPE_LABELS: Record<string, string> = {
  BASE: 'BASE',
  INHERITED: 'INHERITED',
  OVERRIDE: 'OVERRIDE',
  EXPERIMENTAL: 'EXP',
  PUBLISHED: 'PUB',
};

const SceneVariantEditor: React.FC = () => {
  const [variants, setVariants] = useState<SceneVariant[]>([]);
  const [selectedVariantId, setSelectedVariantId] = useState('');
  const [selectedParentId, setSelectedParentId] = useState('');
  const [newName, setNewName] = useState('');
  const [newData, setNewData] = useState('');
  const [overrideKey, setOverrideKey] = useState('');
  const [overrideValue, setOverrideValue] = useState('');
  const [diffVariantA, setDiffVariantA] = useState('');
  const [diffVariantB, setDiffVariantB] = useState('');
  const [mergeStrategy, setMergeStrategy] = useState('KEEP_PARENT');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<VariantStats>({ total: 0, by_type: {} });
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [activeTab, setActiveTab] = useState<'list' | 'tree' | 'diff' | 'stats'>('list');
  const [expandedParents, setExpandedParents] = useState<Set<string>>(new Set());

  const selectedVariant = variants.find(v => v.variant_id === selectedVariantId);

  const apiFetch = useCallback(async (path: string, options?: RequestInit) => {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
    return res.json();
  }, []);

  const loadVariants = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch('/list');
      setVariants(data.variants || data || []);
      if (data.stats) setStats(data.stats);
    } catch {
      setVariants([]);
    }
    setLoading(false);
  }, [apiFetch]);

  const loadStats = useCallback(async () => {
    try {
      const data = await apiFetch('/stats');
      setStats(data);
    } catch {
      const byType: Record<string, number> = {};
      variants.forEach(v => {
        byType[v.variant_type] = (byType[v.variant_type] || 0) + 1;
      });
      setStats({ total: variants.length, by_type: byType });
    }
  }, [apiFetch, variants]);

  useEffect(() => { loadVariants(); }, [loadVariants]);
  useEffect(() => { loadStats(); }, [loadStats]);

  const handleCreateVariant = async () => {
    if (!newName.trim()) { setMessage('Name is required.'); return; }
    setLoading(true);
    try {
      let sceneData: Record<string, unknown> = {};
      if (newData.trim()) {
        try { sceneData = JSON.parse(newData); } catch {
          setMessage('Invalid JSON in scene data.'); setLoading(false); return;
        }
      }
      await apiFetch('/create', {
        method: 'POST',
        body: JSON.stringify({
          name: newName.trim(),
          parent_id: selectedParentId || null,
          scene_data: sceneData,
        }),
      });
      setMessage(`Created variant "${newName.trim()}"`);
      setNewName('');
      setNewData('');
      setSelectedParentId('');
      await loadVariants();
    } catch (e) {
      setMessage(`Failed to create: ${(e as Error).message}`);
    }
    setLoading(false);
  };

  const handleBranchVariant = async () => {
    if (!selectedVariantId || !newName.trim()) {
      setMessage('Select a variant and enter a new name.');
      return;
    }
    setLoading(true);
    try {
      await apiFetch(`/${selectedVariantId}/branch`, {
        method: 'POST',
        body: JSON.stringify({ name: newName.trim() }),
      });
      setMessage(`Branched "${newName.trim()}" from "${selectedVariant?.name}"`);
      setNewName('');
      await loadVariants();
    } catch (e) {
      setMessage(`Failed to branch: ${(e as Error).message}`);
    }
    setLoading(false);
  };

  const handleApplyOverride = async () => {
    if (!selectedVariantId || !overrideKey.trim()) {
      setMessage('Select a variant and enter an override key.');
      return;
    }
    setLoading(true);
    try {
      let parsedValue: unknown = overrideValue.trim();
      try { parsedValue = JSON.parse(overrideValue.trim()); } catch { /* use raw string */ }
      await apiFetch(`/${selectedVariantId}/override`, {
        method: 'POST',
        body: JSON.stringify({ key: overrideKey.trim(), value: parsedValue }),
      });
      setMessage(`Applied override "${overrideKey.trim()}" to "${selectedVariant?.name}"`);
      setOverrideKey('');
      setOverrideValue('');
      await loadVariants();
    } catch (e) {
      setMessage(`Failed to apply override: ${(e as Error).message}`);
    }
    setLoading(false);
  };

  const handleMerge = async () => {
    if (!selectedVariantId) { setMessage('Select a variant to merge.'); return; }
    setLoading(true);
    try {
      await apiFetch(`/${selectedVariantId}/merge`, {
        method: 'POST',
        body: JSON.stringify({ strategy: mergeStrategy }),
      });
      setMessage(`Merged "${selectedVariant?.name}" with strategy ${mergeStrategy}`);
      await loadVariants();
    } catch (e) {
      setMessage(`Failed to merge: ${(e as Error).message}`);
    }
    setLoading(false);
  };

  const handleDiff = async () => {
    if (!diffVariantA || !diffVariantB) {
      setMessage('Select two variants to diff.');
      return;
    }
    setLoading(true);
    try {
      const data: DiffResult = await apiFetch(`/diff/${diffVariantA}/${diffVariantB}`);
      setDiffResult(data);
      setActiveTab('diff');
      setMessage('Diff computed.');
    } catch {
      const vA = variants.find(v => v.variant_id === diffVariantA);
      const vB = variants.find(v => v.variant_id === diffVariantB);
      if (vA && vB) {
        const added: Record<string, unknown> = {};
        const removed: Record<string, unknown> = {};
        const changed: Record<string, { old: unknown; new: unknown }> = {};
        const keysA = Object.keys(vA.scene_data);
        const keysB = Object.keys(vB.scene_data);
        keysB.forEach(k => { if (!keysA.includes(k)) added[k] = vB.scene_data[k]; });
        keysA.forEach(k => { if (!keysB.includes(k)) removed[k] = vA.scene_data[k]; });
        keysA.forEach(k => {
          if (keysB.includes(k) && JSON.stringify(vA.scene_data[k]) !== JSON.stringify(vB.scene_data[k])) {
            changed[k] = { old: vA.scene_data[k], new: vB.scene_data[k] };
          }
        });
        setDiffResult({ added, removed, changed });
        setActiveTab('diff');
        setMessage('Diff computed locally.');
      } else {
        setMessage('Failed to compute diff.');
      }
    }
    setLoading(false);
  };

  const handlePromote = async () => {
    if (!selectedVariantId) { setMessage('Select a variant to promote.'); return; }
    setLoading(true);
    try {
      await apiFetch(`/${selectedVariantId}/promote`, { method: 'POST' });
      setMessage(`Promoted "${selectedVariant?.name}" to PUBLISHED`);
      await loadVariants();
    } catch (e) {
      setMessage(`Failed to promote: ${(e as Error).message}`);
    }
    setLoading(false);
  };

  const handleDelete = async (variantId: string) => {
    const v = variants.find(x => x.variant_id === variantId);
    setLoading(true);
    try {
      await apiFetch(`/${variantId}`, { method: 'DELETE' });
      setMessage(`Deleted variant "${v?.name || variantId}"`);
      if (selectedVariantId === variantId) setSelectedVariantId('');
      await loadVariants();
    } catch (e) {
      setMessage(`Failed to delete: ${(e as Error).message}`);
    }
    setLoading(false);
  };

  const toggleExpand = (id: string) => {
    setExpandedParents(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const getChildVariants = (parentId: string | null): SceneVariant[] =>
    variants.filter(v => v.parent_id === parentId);

  const renderTree = (parentId: string | null, depth: number = 0): React.ReactNode[] => {
    const children = getChildVariants(parentId);
    return children.map(variant => {
      const hasChildren = getChildVariants(variant.variant_id).length > 0;
      const isExpanded = expandedParents.has(variant.variant_id);
      return (
        <React.Fragment key={variant.variant_id}>
          <div
            onClick={() => { setSelectedVariantId(variant.variant_id); toggleExpand(variant.variant_id); }}
            style={{
              paddingLeft: 12 + depth * 20,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 8px 4px ' + (12 + depth * 20) + 'px',
              cursor: 'pointer',
              backgroundColor: selectedVariantId === variant.variant_id ? 'rgba(137,180,250,0.1)' : 'transparent',
              borderLeft: selectedVariantId === variant.variant_id ? '2px solid #89b4fa' : '2px solid transparent',
            }}
          >
            {hasChildren && (
              <span style={{ fontSize: 10, color: '#6c7086', width: 12 }}>
                {isExpanded ? '▼' : '▶'}
              </span>
            )}
            {!hasChildren && <span style={{ width: 12 }} />}
            <span style={{
              display: 'inline-block',
              padding: '1px 6px',
              borderRadius: 3,
              fontSize: 9,
              fontWeight: 700,
              backgroundColor: TYPE_COLORS[variant.variant_type] + '30',
              color: TYPE_COLORS[variant.variant_type],
              border: '1px solid ' + TYPE_COLORS[variant.variant_type] + '50',
            }}>
              {TYPE_LABELS[variant.variant_type]}
            </span>
            <span style={{ fontSize: 12, color: '#cdd6f4' }}>{variant.name}</span>
          </div>
          {hasChildren && isExpanded && renderTree(variant.variant_id, depth + 1)}
        </React.Fragment>
      );
    });
  };

  const rootVariants = getChildVariants(null);

  return (
    <div style={{
      height: '100%',
      backgroundColor: '#1e1e2e',
      color: '#cdd6f4',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      fontFamily: "'SF Mono', 'Fira Code', monospace",
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 16px',
        borderBottom: '1px solid #45475a',
      }}>
        <h3 style={{ fontSize: 13, fontWeight: 700, color: '#89b4fa', margin: 0 }}>
          Scene Variants
        </h3>
        <div style={{ flex: 1 }} />
        {loading && <span style={{ fontSize: 11, color: '#6c7086' }}>Loading...</span>}
      </div>

      <div style={{
        display: 'flex',
        borderBottom: '1px solid #45475a',
        padding: '0 16px',
        gap: 0,
      }}>
        {(['list', 'tree', 'diff', 'stats'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '6px 14px',
              fontSize: 11,
              fontWeight: 600,
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid #89b4fa' : '2px solid transparent',
              backgroundColor: 'transparent',
              color: activeTab === tab ? '#89b4fa' : '#6c7086',
              cursor: 'pointer',
              textTransform: 'uppercase',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {message && (
        <div style={{
          margin: '8px 16px 0',
          padding: '6px 12px',
          borderRadius: 4,
          fontSize: 11,
          backgroundColor: '#313244',
          color: '#a6e3a1',
          border: '1px solid #45475a',
        }}>
          {message}
        </div>
      )}

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{
          width: 280,
          borderRight: '1px solid #45475a',
          overflowY: 'auto',
          padding: 8,
          flexShrink: 0,
        }}>
          {activeTab === 'list' && (
            <>
              <div style={{ fontWeight: 600, fontSize: 11, color: '#6c7086', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
                Variants ({variants.length})
              </div>
              {rootVariants.length === 0 && !loading && (
                <div style={{ fontSize: 11, color: '#585b70', padding: 8, textAlign: 'center' }}>
                  No variants yet
                </div>
              )}
              {rootVariants.map(v => (
                <div
                  key={v.variant_id}
                  onClick={() => setSelectedVariantId(v.variant_id)}
                  style={{
                    padding: '8px 10px',
                    marginBottom: 4,
                    borderRadius: 4,
                    cursor: 'pointer',
                    backgroundColor: selectedVariantId === v.variant_id ? '#313244' : '#2a2a3e',
                    border: selectedVariantId === v.variant_id ? '1px solid #89b4fa' : '1px solid #45475a',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <span style={{
                      display: 'inline-block',
                      padding: '1px 6px',
                      borderRadius: 3,
                      fontSize: 9,
                      fontWeight: 700,
                      backgroundColor: TYPE_COLORS[v.variant_type] + '30',
                      color: TYPE_COLORS[v.variant_type],
                      border: '1px solid ' + TYPE_COLORS[v.variant_type] + '50',
                    }}>
                      {TYPE_LABELS[v.variant_type]}
                    </span>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{v.name}</span>
                  </div>
                  {v.parent_id && (
                    <div style={{ fontSize: 10, color: '#6c7086' }}>
                      parent: {variants.find(p => p.variant_id === v.parent_id)?.name || v.parent_id}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}

          {activeTab === 'tree' && (
            <>
              <div style={{ fontWeight: 600, fontSize: 11, color: '#6c7086', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
                Variant Tree
              </div>
              {rootVariants.length === 0 && !loading && (
                <div style={{ fontSize: 11, color: '#585b70', padding: 8, textAlign: 'center' }}>
                  No variants in tree
                </div>
              )}
              {renderTree(null)}
            </>
          )}

          {activeTab === 'diff' && (
            <div style={{ padding: 4 }}>
              <div style={{ fontWeight: 600, fontSize: 11, color: '#6c7086', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                Diff Selector
              </div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ fontSize: 10, color: '#a6adc8', display: 'block', marginBottom: 4 }}>Variant A (base)</label>
                <select
                  value={diffVariantA}
                  onChange={e => setDiffVariantA(e.target.value)}
                  style={{
                    width: '100%', padding: '4px 6px', fontSize: 11,
                    backgroundColor: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4,
                  }}
                >
                  <option value="">-- Select --</option>
                  {variants.map(v => (
                    <option key={v.variant_id} value={v.variant_id}>{v.name}</option>
                  ))}
                </select>
              </div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ fontSize: 10, color: '#a6adc8', display: 'block', marginBottom: 4 }}>Variant B (compare)</label>
                <select
                  value={diffVariantB}
                  onChange={e => setDiffVariantB(e.target.value)}
                  style={{
                    width: '100%', padding: '4px 6px', fontSize: 11,
                    backgroundColor: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4,
                  }}
                >
                  <option value="">-- Select --</option>
                  {variants.map(v => (
                    <option key={v.variant_id} value={v.variant_id}>{v.name}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleDiff}
                style={{
                  width: '100%', padding: '6px 0', fontSize: 11, fontWeight: 600,
                  backgroundColor: '#89b4fa', color: '#1e1e2e', border: 'none', borderRadius: 4, cursor: 'pointer',
                }}
              >
                Compute Diff
              </button>
            </div>
          )}

          {activeTab === 'stats' && (
            <div style={{ padding: 4 }}>
              <div style={{ fontWeight: 600, fontSize: 11, color: '#6c7086', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                Statistics
              </div>
              <div style={{
                padding: 10, borderRadius: 4, backgroundColor: '#2a2a3e', border: '1px solid #45475a', marginBottom: 8,
              }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#89b4fa' }}>{stats.total}</div>
                <div style={{ fontSize: 10, color: '#6c7086' }}>Total Variants</div>
              </div>
              {Object.entries(stats.by_type).map(([type, count]) => (
                <div key={type} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '6px 8px', marginBottom: 3, borderRadius: 3,
                  backgroundColor: '#2a2a3e', border: '1px solid #45475a',
                }}>
                  <span style={{
                    padding: '1px 6px', borderRadius: 3, fontSize: 9, fontWeight: 700,
                    backgroundColor: TYPE_COLORS[type] + '30', color: TYPE_COLORS[type],
                    border: '1px solid ' + TYPE_COLORS[type] + '50',
                  }}>
                    {type}
                  </span>
                  <span style={{ fontSize: 14, fontWeight: 700, color: TYPE_COLORS[type] }}>{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
          {activeTab === 'diff' && diffResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ fontWeight: 600, fontSize: 12, color: '#89b4fa', marginBottom: 2 }}>Diff Results</div>

              {Object.keys(diffResult.added).length > 0 && (
                <div style={{
                  padding: 10, borderRadius: 4, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
                }}>
                  <div style={{ fontWeight: 700, fontSize: 11, color: '#a6e3a1', marginBottom: 6 }}>
                    + Added ({Object.keys(diffResult.added).length})
                  </div>
                  {Object.entries(diffResult.added).map(([key, value]) => (
                    <div key={key} style={{ fontSize: 10, marginBottom: 3, paddingLeft: 8 }}>
                      <span style={{ color: '#a6e3a1', fontWeight: 600 }}>{key}</span>
                      <span style={{ color: '#6c7086' }}>: </span>
                      <span style={{ color: '#cdd6f4' }}>{JSON.stringify(value)}</span>
                    </div>
                  ))}
                </div>
              )}

              {Object.keys(diffResult.removed).length > 0 && (
                <div style={{
                  padding: 10, borderRadius: 4, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
                }}>
                  <div style={{ fontWeight: 700, fontSize: 11, color: '#f38ba8', marginBottom: 6 }}>
                    - Removed ({Object.keys(diffResult.removed).length})
                  </div>
                  {Object.entries(diffResult.removed).map(([key, value]) => (
                    <div key={key} style={{ fontSize: 10, marginBottom: 3, paddingLeft: 8 }}>
                      <span style={{ color: '#f38ba8', fontWeight: 600 }}>{key}</span>
                      <span style={{ color: '#6c7086' }}>: </span>
                      <span style={{ color: '#cdd6f4' }}>{JSON.stringify(value)}</span>
                    </div>
                  ))}
                </div>
              )}

              {Object.keys(diffResult.changed).length > 0 && (
                <div style={{
                  padding: 10, borderRadius: 4, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
                }}>
                  <div style={{ fontWeight: 700, fontSize: 11, color: '#f9e2af', marginBottom: 6 }}>
                    ~ Changed ({Object.keys(diffResult.changed).length})
                  </div>
                  {Object.entries(diffResult.changed).map(([key, { old: oldVal, new: newVal }]) => (
                    <div key={key} style={{ fontSize: 10, marginBottom: 4, paddingLeft: 8 }}>
                      <span style={{ color: '#f9e2af', fontWeight: 600 }}>{key}</span>
                      <div style={{ display: 'flex', gap: 12, marginTop: 2 }}>
                        <span style={{ color: '#f38ba8' }}>- {JSON.stringify(oldVal)}</span>
                        <span style={{ color: '#a6e3a1' }}>+ {JSON.stringify(newVal)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {Object.keys(diffResult.added).length === 0 && Object.keys(diffResult.removed).length === 0 && Object.keys(diffResult.changed).length === 0 && (
                <div style={{ fontSize: 11, color: '#6c7086', padding: 16, textAlign: 'center' }}>
                  No differences found
                </div>
              )}
            </div>
          )}

          {activeTab !== 'diff' && (
            <>
              {selectedVariant ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={{
                    padding: 12, borderRadius: 6, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 3, fontSize: 10, fontWeight: 700,
                        backgroundColor: TYPE_COLORS[selectedVariant.variant_type] + '30',
                        color: TYPE_COLORS[selectedVariant.variant_type],
                        border: '1px solid ' + TYPE_COLORS[selectedVariant.variant_type] + '50',
                      }}>
                        {selectedVariant.variant_type}
                      </span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#cdd6f4' }}>{selectedVariant.name}</span>
                    </div>
                    {selectedVariant.parent_id && (
                      <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>
                        Parent: {variants.find(p => p.variant_id === selectedVariant.parent_id)?.name || selectedVariant.parent_id}
                      </div>
                    )}
                    <div style={{ fontSize: 10, color: '#585b70' }}>
                      ID: {selectedVariant.variant_id}
                    </div>
                  </div>

                  <div style={{
                    padding: 10, borderRadius: 4, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
                  }}>
                    <div style={{ fontWeight: 600, fontSize: 10, color: '#a6adc8', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
                      Scene Data
                    </div>
                    <pre style={{
                      margin: 0, fontSize: 10, color: '#cdd6f4',
                      maxHeight: 120, overflow: 'auto', whiteSpace: 'pre-wrap',
                    }}>
                      {JSON.stringify(selectedVariant.scene_data || {}, null, 2)}
                    </pre>
                  </div>

                  {Object.keys(selectedVariant.overrides || {}).length > 0 && (
                    <div style={{
                      padding: 10, borderRadius: 4, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
                    }}>
                      <div style={{ fontWeight: 600, fontSize: 10, color: '#f9e2af', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
                        Overrides
                      </div>
                      {Object.entries(selectedVariant.overrides).map(([key, value]) => (
                        <div key={key} style={{ fontSize: 10, marginBottom: 2 }}>
                          <span style={{ color: '#f9e2af', fontWeight: 600 }}>{key}</span>
                          <span style={{ color: '#6c7086' }}>: </span>
                          <span style={{ color: '#cdd6f4' }}>{JSON.stringify(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <button
                      onClick={handlePromote}
                      disabled={selectedVariant.variant_type === 'PUBLISHED'}
                      style={{
                        padding: '5px 10px', fontSize: 10, fontWeight: 600,
                        backgroundColor: selectedVariant.variant_type === 'PUBLISHED' ? '#45475a' : '#f5c266',
                        color: selectedVariant.variant_type === 'PUBLISHED' ? '#6c7086' : '#1e1e2e',
                        border: 'none', borderRadius: 4, cursor: selectedVariant.variant_type === 'PUBLISHED' ? 'not-allowed' : 'pointer',
                      }}
                    >
                      Promote to Published
                    </button>
                    <button
                      onClick={() => handleDelete(selectedVariant.variant_id)}
                      style={{
                        padding: '5px 10px', fontSize: 10, fontWeight: 600,
                        backgroundColor: '#f38ba8', color: '#1e1e2e', border: 'none', borderRadius: 4, cursor: 'pointer',
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: 11, color: '#585b70', padding: 24, textAlign: 'center' }}>
                  Select a variant to view details
                </div>
              )}
            </>
          )}
        </div>

        <div style={{
          width: 300,
          borderLeft: '1px solid #45475a',
          overflowY: 'auto',
          padding: 10,
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}>
          <div style={{
            padding: 10, borderRadius: 6, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
          }}>
            <div style={{ fontWeight: 600, fontSize: 11, color: '#89b4fa', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
              Create Variant
            </div>
            <input
              placeholder="Variant name"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box', padding: '5px 8px', fontSize: 11,
                backgroundColor: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4,
                marginBottom: 6,
              }}
            />
            <select
              value={selectedParentId}
              onChange={e => setSelectedParentId(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box', padding: '5px 8px', fontSize: 11,
                backgroundColor: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4,
                marginBottom: 6,
              }}
            >
              <option value="">No parent</option>
              {variants.map(v => (
                <option key={v.variant_id} value={v.variant_id}>{v.name}</option>
              ))}
            </select>
            <textarea
              placeholder='Scene data (JSON, e.g. {"foo": "bar"})'
              value={newData}
              onChange={e => setNewData(e.target.value)}
              rows={4}
              style={{
                width: '100%', boxSizing: 'border-box', padding: '5px 8px', fontSize: 10,
                backgroundColor: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4,
                resize: 'vertical', marginBottom: 6, fontFamily: 'inherit',
              }}
            />
            <button
              onClick={handleCreateVariant}
              style={{
                width: '100%', padding: '6px 0', fontSize: 11, fontWeight: 600,
                backgroundColor: '#89b4fa', color: '#1e1e2e', border: 'none', borderRadius: 4, cursor: 'pointer',
              }}
            >
              Create
            </button>
          </div>

          <div style={{
            padding: 10, borderRadius: 6, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
          }}>
            <div style={{ fontWeight: 600, fontSize: 11, color: '#a6e3a1', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
              Branch Variant
            </div>
            <input
              placeholder="New branch name"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box', padding: '5px 8px', fontSize: 11,
                backgroundColor: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4,
                marginBottom: 6,
              }}
            />
            <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 6 }}>
              Source: {selectedVariant ? selectedVariant.name : 'none selected'}
            </div>
            <button
              onClick={handleBranchVariant}
              style={{
                width: '100%', padding: '6px 0', fontSize: 11, fontWeight: 600,
                backgroundColor: '#a6e3a1', color: '#1e1e2e', border: 'none', borderRadius: 4, cursor: 'pointer',
              }}
            >
              Branch
            </button>
          </div>

          <div style={{
            padding: 10, borderRadius: 6, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
          }}>
            <div style={{ fontWeight: 600, fontSize: 11, color: '#f9e2af', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
              Apply Override
            </div>
            <input
              placeholder="Key path (e.g. lighting.ambient)"
              value={overrideKey}
              onChange={e => setOverrideKey(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box', padding: '5px 8px', fontSize: 11,
                backgroundColor: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4,
                marginBottom: 6,
              }}
            />
            <input
              placeholder="Value (string or JSON)"
              value={overrideValue}
              onChange={e => setOverrideValue(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box', padding: '5px 8px', fontSize: 11,
                backgroundColor: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4,
                marginBottom: 6,
              }}
            />
            <button
              onClick={handleApplyOverride}
              style={{
                width: '100%', padding: '6px 0', fontSize: 11, fontWeight: 600,
                backgroundColor: '#f9e2af', color: '#1e1e2e', border: 'none', borderRadius: 4, cursor: 'pointer',
              }}
            >
              Apply Override
            </button>
          </div>

          <div style={{
            padding: 10, borderRadius: 6, backgroundColor: '#2a2a3e', border: '1px solid #45475a',
          }}>
            <div style={{ fontWeight: 600, fontSize: 11, color: '#cba6f7', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
              Merge Variant
            </div>
            <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 6 }}>
              Target: {selectedVariant ? selectedVariant.name : 'none selected'}
            </div>
            <select
              value={mergeStrategy}
              onChange={e => setMergeStrategy(e.target.value)}
              style={{
                width: '100%', boxSizing: 'border-box', padding: '5px 8px', fontSize: 11,
                backgroundColor: '#313244', color: '#cdd6f4', border: '1px solid #45475a', borderRadius: 4,
                marginBottom: 6,
              }}
            >
              <option value="KEEP_PARENT">KEEP_PARENT</option>
              <option value="KEEP_CHILD">KEEP_CHILD</option>
              <option value="KEEP_BOTH">KEEP_BOTH</option>
              <option value="MANUAL">MANUAL</option>
            </select>
            <button
              onClick={handleMerge}
              style={{
                width: '100%', padding: '6px 0', fontSize: 11, fontWeight: 600,
                backgroundColor: '#cba6f7', color: '#1e1e2e', border: 'none', borderRadius: 4, cursor: 'pointer',
              }}
            >
              Merge
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SceneVariantEditor;