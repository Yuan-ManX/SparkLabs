import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface AssetDescriptor {
  id: string;
  name: string;
  asset_type: string;
  category: string;
  dimensions: Record<string, string>;
}

interface CompatibilityResult {
  is_compatible: boolean;
  overall_compatibility: number;
  conflicts: string[];
  dimension_scores: Record<string, number>;
}

const ASSET_TYPES = ['3d_model', 'texture', 'audio', 'animation', 'script', 'ui_element', 'particle_system', 'sprite'];
const ASSET_CATEGORIES = ['character', 'environment', 'prop', 'ui', 'vfx', 'audio', 'gameplay', 'cinematic'];

const DIMENSION_OPTIONS: Record<string, string[]> = {
  visual_style: ['stylized_cartoon', 'realistic', 'low_poly', 'pixel_art', 'cel_shaded', 'hand_painted', 'photorealistic'],
  color_palette: ['warm', 'cool', 'monochrome', 'vibrant', 'pastel', 'dark', 'earthy', 'neon'],
  spatial_coherence: ['grid_aligned', 'free_placement', 'organic', 'architectural', 'natural'],
  scale_consistency: ['miniature', 'normal', 'large', 'epic', 'variable'],
  material_quality: ['low', 'medium', 'high', 'ultra', 'stylized'],
  animation_style: ['none', 'keyframe', 'procedural', 'motion_capture', 'physics_based'],
  audio_profile: ['none', 'ambient', 'orchestral', 'electronic', 'diegetic', 'ui_sounds'],
};

const CATEGORY_COLORS: Record<string, string> = {
  character: '#60a5fa', environment: '#34d399', prop: '#fbbf24',
  ui: '#a78bfa', vfx: '#f97316', audio: '#ec4899',
  gameplay: '#3b82f6', cinematic: '#f59e0b',
};

const AssetHarmonizerPanel: React.FC = () => {
  const [assets, setAssets] = useState<AssetDescriptor[]>([]);
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [message, setMessage] = useState('');

  const [assetName, setAssetName] = useState('');
  const [assetType, setAssetType] = useState('3d_model');
  const [assetCategory, setAssetCategory] = useState('character');
  const [dimensions, setDimensions] = useState<Record<string, string>>({});

  const [checkAId, setCheckAId] = useState('');
  const [checkBId, setCheckBId] = useState('');
  const [compatResult, setCompatResult] = useState<CompatibilityResult | null>(null);

  const [batchResults, setBatchResults] = useState<CompatibilityResult[]>([]);
  const [clashingPairs, setClashingPairs] = useState<{ a: string; b: string; score: number }[]>([]);

  const loadStats = useCallback(async () => {
    try {
      const data = await engineApi.harmonizerStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ total_assets: 0, compatibility_checks: 0 });
    }
  }, []);

  const loadAssets = useCallback(async () => {
    try {
      const data = await engineApi.harmonizerList();
      const list = data.assets || data || [];
      setAssets(list as AssetDescriptor[]);
    } catch {}
  }, []);

  useEffect(() => { loadStats(); loadAssets(); }, [loadStats, loadAssets]);

  const handleDimensionChange = (dimKey: string, value: string) => {
    setDimensions(prev => ({ ...prev, [dimKey]: value }));
  };

  const handleRegister = async () => {
    if (!assetName.trim()) return;
    try {
      const result = await engineApi.harmonizerRegister(
        assetName.trim(), assetType, assetCategory, dimensions
      );
      setMessage(`Registered: ${assetName}`);
      setAssetName('');
      setDimensions({});
      loadAssets();
      loadStats();
    } catch { setMessage('Failed to register asset.'); }
  };

  const handleCheckCompatibility = async () => {
    if (!checkAId || !checkBId) return;
    try {
      const result = await engineApi.harmonizerCheck(checkAId, checkBId);
      setCompatResult(result as CompatibilityResult);
      setMessage(
        (result as any).is_compatible
          ? `Compatible! Score: ${((result as any).overall_compatibility * 100).toFixed(0)}%`
          : `Conflicts found. Score: ${((result as any).overall_compatibility * 100).toFixed(0)}%`
      );
    } catch {
      setMessage('Compatibility check failed.');
    }
  };

  const handleBatchCheck = async () => {
    if (assets.length < 2) {
      setMessage('Need at least 2 assets for batch check.');
      return;
    }
    try {
      const results: CompatibilityResult[] = [];
      const clashing: { a: string; b: string; score: number }[] = [];
      for (let i = 0; i < assets.length; i++) {
        for (let j = i + 1; j < assets.length; j++) {
          const result = await engineApi.harmonizerCheck(assets[i].id, assets[j].id);
          results.push(result as CompatibilityResult);
          if (!(result as any).is_compatible) {
            clashing.push({
              a: assets[i].name, b: assets[j].name,
              score: (result as any).overall_compatibility,
            });
          }
        }
      }
      setBatchResults(results);
      setClashingPairs(clashing);
      setMessage(`Batch check complete: ${clashing.length} clashing pairs found.`);
    } catch {
      setMessage('Batch check failed.');
    }
  };

  const assetAName = assets.find(a => a.id === checkAId)?.name || '';
  const assetBName = assets.find(a => a.id === checkBId)?.name || '';

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#ec4899' }}>Asset Harmonizer</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Assets</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.total_assets || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Checks</div>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#ec4899' }}>{stats.compatibility_checks || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 60 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Avg Score</div>
            <div style={{ fontSize: 18, fontWeight: 'bold', color: '#34d399' }}>
              {stats.avg_compatibility ? `${(stats.avg_compatibility * 100).toFixed(0)}%` : 'N/A'}
            </div>
          </div>
        </div>
      )}

      <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>Register Asset</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 6 }}>
          <input
            value={assetName}
            onChange={e => setAssetName(e.target.value)}
            placeholder="Asset name"
            style={{
              padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
              background: '#111', color: '#e0e0e0', fontSize: 11,
            }}
          />
          <select
            value={assetType}
            onChange={e => setAssetType(e.target.value)}
            style={{
              padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
              background: '#111', color: '#60a5fa', fontSize: 11,
            }}
          >
            {ASSET_TYPES.map(t => (
              <option key={t} value={t}>{t.replace('_', ' ')}</option>
            ))}
          </select>
        </div>
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>Category</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {ASSET_CATEGORIES.map(cat => (
              <button
                key={cat}
                onClick={() => setAssetCategory(cat)}
                style={{
                  padding: '3px 10px', borderRadius: 6, fontSize: 10,
                  border: assetCategory === cat ? `2px solid ${CATEGORY_COLORS[cat]}` : '1px solid #333',
                  background: assetCategory === cat ? CATEGORY_COLORS[cat] + '22' : '#111',
                  color: assetCategory === cat ? CATEGORY_COLORS[cat] : '#888',
                  cursor: 'pointer',
                }}
              >{cat}</button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>Dimensions</div>
          {Object.entries(DIMENSION_OPTIONS).map(([dimKey, options]) => (
            <div key={dimKey} style={{ marginBottom: 6 }}>
              <div style={{ fontSize: 10, color: '#666', marginBottom: 3 }}>
                {dimKey.replace(/_/g, ' ')}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {options.map(opt => {
                  const isSelected = dimensions[dimKey] === opt;
                  return (
                    <button
                      key={opt}
                      onClick={() => handleDimensionChange(dimKey, isSelected ? '' : opt)}
                      style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 9,
                        border: isSelected ? '2px solid #ec4899' : '1px solid #333',
                        background: isSelected ? '#2a1a2a' : '#111',
                        color: isSelected ? '#ec4899' : '#777',
                        cursor: 'pointer',
                      }}
                    >{opt.replace(/_/g, ' ')}</button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <button onClick={handleRegister} style={{
          padding: '6px 16px', borderRadius: 6, border: 'none', background: '#ec4899',
          color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 'bold',
        }}>Register Asset</button>
      </div>

      <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
          Registered Assets ({assets.length})
        </div>
        {assets.map(asset => {
          const dimKeys = Object.keys(asset.dimensions || {});
          return (
            <div key={asset.id} style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
              marginBottom: 4, background: '#111', borderRadius: 6,
              borderLeft: `3px solid ${CATEGORY_COLORS[asset.category] || '#ec4899'}`,
            }}>
              <span style={{
                fontSize: 9, padding: '1px 6px', borderRadius: 3,
                background: CATEGORY_COLORS[asset.category] + '22',
                color: CATEGORY_COLORS[asset.category],
              }}>{asset.asset_type.replace('_', ' ')}</span>
              <span style={{ fontSize: 12, color: '#e0e0e0', flex: 1 }}>{asset.name}</span>
              <span style={{ fontSize: 10, color: '#666' }}>{asset.category}</span>
              {dimKeys.length > 0 && (
                <div style={{ display: 'flex', gap: 3 }}>
                  {dimKeys.slice(0, 3).map(dk => (
                    <span key={dk} style={{
                      fontSize: 8, padding: '1px 4px', borderRadius: 3,
                      background: '#1a1a3e', color: '#aaa',
                    }}>{asset.dimensions[dk]}</span>
                  ))}
                  {dimKeys.length > 3 && (
                    <span style={{ fontSize: 8, color: '#555' }}>+{dimKeys.length - 3}</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ccc', marginBottom: 8 }}>
          Compatibility Checker
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
          <select
            value={checkAId}
            onChange={e => setCheckAId(e.target.value)}
            style={{
              padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
              background: '#111', color: '#e0e0e0', fontSize: 11,
            }}
          >
            <option value="">Asset A</option>
            {assets.map(a => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <select
            value={checkBId}
            onChange={e => setCheckBId(e.target.value)}
            style={{
              padding: '4px 8px', borderRadius: 4, border: '1px solid #333',
              background: '#111', color: '#e0e0e0', fontSize: 11,
            }}
          >
            <option value="">Asset B</option>
            {assets.map(a => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={handleCheckCompatibility} style={{
            padding: '5px 14px', borderRadius: 6, border: 'none', background: '#8b5cf6',
            color: '#fff', cursor: 'pointer', fontSize: 11,
          }}>Check Pair</button>
          <button onClick={handleBatchCheck} style={{
            padding: '5px 14px', borderRadius: 6, border: '1px solid #ec4899',
            background: 'transparent', color: '#ec4899', cursor: 'pointer', fontSize: 11,
          }}>Batch Check All</button>
        </div>

        {compatResult && (
          <div style={{ marginTop: 10, padding: 10, background: '#111', borderRadius: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: '#ccc' }}>{assetAName}</span>
              <span style={{ fontSize: 10, color: '#555' }}>vs</span>
              <span style={{ fontSize: 12, color: '#ccc' }}>{assetBName}</span>
              <span style={{
                marginLeft: 'auto', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 'bold',
                background: compatResult.is_compatible ? '#1a2a1a' : '#2a1a1a',
                color: compatResult.is_compatible ? '#34d399' : '#ef4444',
              }}>
                {compatResult.is_compatible ? '✓ Compatible' : '✗ Conflict'}
              </span>
            </div>

            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>Overall Score</div>
              <div style={{
                height: 6, borderRadius: 3, background: '#222', overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%', borderRadius: 3,
                  width: `${(compatResult.overall_compatibility * 100).toFixed(0)}%`,
                  background: compatResult.is_compatible ? '#34d399' : '#ef4444',
                  transition: 'width 0.3s',
                }} />
              </div>
              <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>
                {(compatResult.overall_compatibility * 100).toFixed(0)}%
              </div>
            </div>

            {compatResult.dimension_scores && Object.keys(compatResult.dimension_scores).length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>Dimension Scores</div>
                {Object.entries(compatResult.dimension_scores).map(([dim, score]) => (
                  <div key={dim} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                    <span style={{ fontSize: 10, color: '#aaa', minWidth: 110 }}>{dim.replace(/_/g, ' ')}</span>
                    <div style={{ flex: 1, height: 4, borderRadius: 2, background: '#222', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', borderRadius: 2,
                        width: `${(score * 100).toFixed(0)}%`,
                        background: score >= 0.7 ? '#34d399' : score >= 0.4 ? '#fbbf24' : '#ef4444',
                      }} />
                    </div>
                    <span style={{ fontSize: 10, color: '#888', minWidth: 30 }}>{(score * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}

            {compatResult.conflicts && compatResult.conflicts.length > 0 && (
              <div>
                <div style={{ fontSize: 10, color: '#ef4444', marginBottom: 4 }}>Conflicts</div>
                {compatResult.conflicts.map((conflict, i) => (
                  <div key={i} style={{
                    padding: '3px 8px', marginBottom: 3, background: '#2a1a1a',
                    borderRadius: 4, fontSize: 10, color: '#ef4444',
                  }}>{conflict}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {clashingPairs.length > 0 && (
        <div style={{ background: '#1a1a2e', borderRadius: 8, padding: 12, marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 'bold', color: '#ef4444', marginBottom: 8 }}>
            Clashing Pairs ({clashingPairs.length})
          </div>
          {clashingPairs.map((pair, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px',
              marginBottom: 3, background: '#2a1a1a', borderRadius: 4, fontSize: 11,
            }}>
              <span style={{ color: '#e0e0e0' }}>{pair.a}</span>
              <span style={{ color: '#ef4444' }}>↔</span>
              <span style={{ color: '#e0e0e0' }}>{pair.b}</span>
              <span style={{ marginLeft: 'auto', color: '#ef4444', fontSize: 10 }}>
                {(pair.score * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {message && (
        <div style={{ padding: 8, background: compatResult?.is_compatible ? '#1a2a1a' : '#1a2a1a', borderRadius: 6, color: '#10b981', fontSize: 12 }}>
          {message}
        </div>
      )}
    </div>
  );
};

export default AssetHarmonizerPanel;