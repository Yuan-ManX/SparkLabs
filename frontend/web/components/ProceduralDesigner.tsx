import React, { useState, useCallback, useEffect } from 'react';

interface ProceduralParams {
  id: string;
  algorithm: string;
  category: string;
  seed: number;
  resolution: string;
  overrides: Record<string, string>;
  mutation_strength: number;
}

interface GenerationResult {
  id: string;
  params_id: string;
  output_description: string;
  quality_score: number;
  generation_time_ms: number;
  memory_usage_mb: number;
  created_at: string;
  algorithm: string;
  category: string;
  seed: number;
  is_mutation: boolean;
}

interface DiffReport {
  field: string;
  result_a: string;
  result_b: string;
  diff_type: 'added' | 'removed' | 'changed';
}

interface Stats {
  total_generations: number;
  algorithm_distribution: Record<string, number>;
  average_quality: number;
  total_time_ms: number;
}

type AlgorithmId = 'cellular_automata' | 'wave_function_collapse' | 'l_system' | 'perlin_noise' | 'voronoi' | 'diamond_square' | 'poisson_disc' | 'markov_chain';
type CategoryId = 'terrain' | 'dungeon' | 'vegetation' | 'buildings' | 'rivers' | 'biomes' | 'paths' | 'decorations';

interface AlgorithmDef {
  id: AlgorithmId;
  label: string;
  description: string;
}

interface CategoryDef {
  id: CategoryId;
  label: string;
}

interface PresetDef {
  id: string;
  label: string;
  algorithm: AlgorithmId;
  category: CategoryId;
  seed: number;
  resolution: string;
  description: string;
}

const ALGORITHMS: AlgorithmDef[] = [
  { id: 'cellular_automata', label: 'Cellular Automata', description: 'Grid-based simulation using neighbor rules' },
  { id: 'wave_function_collapse', label: 'Wave Function Collapse', description: 'Constraint-based pattern generation' },
  { id: 'l_system', label: 'L-System', description: 'Recursive string rewriting for organic structures' },
  { id: 'perlin_noise', label: 'Perlin Noise', description: 'Gradient noise for natural-looking terrain' },
  { id: 'voronoi', label: 'Voronoi Diagram', description: 'Cell-based partitioning for regions' },
  { id: 'diamond_square', label: 'Diamond Square', description: 'Midpoint displacement for heightmaps' },
  { id: 'poisson_disc', label: 'Poisson Disc Sampling', description: 'Evenly distributed random points' },
  { id: 'markov_chain', label: 'Markov Chain', description: 'Probabilistic state transitions' },
];

const CATEGORIES: CategoryDef[] = [
  { id: 'terrain', label: 'Terrain' },
  { id: 'dungeon', label: 'Dungeon' },
  { id: 'vegetation', label: 'Vegetation' },
  { id: 'buildings', label: 'Buildings' },
  { id: 'rivers', label: 'Rivers' },
  { id: 'biomes', label: 'Biomes' },
  { id: 'paths', label: 'Paths' },
  { id: 'decorations', label: 'Decorations' },
];

const ALGORITHM_CATEGORY_COMPAT: Record<AlgorithmId, CategoryId[]> = {
  cellular_automata: ['terrain', 'dungeon'],
  wave_function_collapse: ['buildings', 'dungeon', 'paths', 'decorations'],
  l_system: ['vegetation', 'rivers', 'decorations'],
  perlin_noise: ['terrain', 'biomes'],
  voronoi: ['terrain', 'biomes', 'rivers'],
  diamond_square: ['terrain', 'biomes'],
  poisson_disc: ['vegetation', 'decorations', 'buildings'],
  markov_chain: ['dungeon', 'biomes', 'paths'],
};

const PRESETS: PresetDef[] = [
  { id: 'preset_mountain', label: 'Mountain Range', algorithm: 'diamond_square', category: 'terrain', seed: 42, resolution: '1024x1024', description: 'Procedural mountain terrain with ridges' },
  { id: 'preset_dungeon', label: 'Classic Dungeon', algorithm: 'cellular_automata', category: 'dungeon', seed: 137, resolution: '512x512', description: 'Cellular automata cave system' },
  { id: 'preset_forest', label: 'Dense Forest', algorithm: 'l_system', category: 'vegetation', seed: 256, resolution: '2048x2048', description: 'L-system tree and foliage generation' },
  { id: 'preset_city', label: 'City Blocks', algorithm: 'wave_function_collapse', category: 'buildings', seed: 99, resolution: '2048x2048', description: 'WFC urban layout with districts' },
  { id: 'preset_river', label: 'River Network', algorithm: 'voronoi', category: 'rivers', seed: 512, resolution: '1024x1024', description: 'Voronoi-based river basin system' },
  { id: 'preset_biome', label: 'Climate Biomes', algorithm: 'perlin_noise', category: 'biomes', seed: 789, resolution: '4096x4096', description: 'Multi-octave Perlin biome map' },
  { id: 'preset_village', label: 'Poisson Village', algorithm: 'poisson_disc', category: 'decorations', seed: 300, resolution: '1024x1024', description: 'Evenly spaced decorative object placement' },
  { id: 'preset_paths', label: 'Road Network', algorithm: 'markov_chain', category: 'paths', seed: 445, resolution: '2048x2048', description: 'Markov state transitions for road generation' },
];

const STYLES = {
  bg: '#1e1e2e',
  card: '#2a2a3e',
  text: '#cdd6f4',
  border: '#45475a',
  accent: '#89b4fa',
  green: '#a6e3a1',
  red: '#f38ba8',
  yellow: '#f9e2af',
  purple: '#cba6f7',
};

const API_BASE = 'http://localhost:8000/api/agent/procedural-design';

const ProceduralDesigner: React.FC = () => {
  const [generators, setGenerators] = useState<ProceduralParams[]>([]);
  const [results, setResults] = useState<GenerationResult[]>([]);
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<AlgorithmId>('perlin_noise');
  const [selectedCategory, setSelectedCategory] = useState<CategoryId>('terrain');
  const [seed, setSeed] = useState<number>(42);
  const [resolution, setResolution] = useState('1024x1024');
  const [overrides, setOverrides] = useState<{ key: string; value: string }[]>([]);
  const [mutationStrength, setMutationStrength] = useState(0.1);
  const [compareResultA, setCompareResultA] = useState('');
  const [compareResultB, setCompareResultB] = useState('');
  const [diffResult, setDiffResult] = useState<DiffReport[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Stats>({
    total_generations: 0,
    algorithm_distribution: {},
    average_quality: 0,
    total_time_ms: 0,
  });
  const [activeTab, setActiveTab] = useState<'generate' | 'history' | 'compare' | 'export'>('generate');

  const showMessage = (msg: string, isError = false) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), 4000);
  };

  const recalcStats = useCallback((resList: GenerationResult[]) => {
    const dist: Record<string, number> = {};
    let totalQuality = 0;
    let totalTime = 0;
    for (const r of resList) {
      dist[r.algorithm] = (dist[r.algorithm] || 0) + 1;
      totalQuality += r.quality_score;
      totalTime += r.generation_time_ms;
    }
    setStats({
      total_generations: resList.length,
      algorithm_distribution: dist,
      average_quality: resList.length > 0 ? totalQuality / resList.length : 0,
      total_time_ms: totalTime,
    });
  }, []);

  const compatAlgorithms = ALGORITHMS.filter((a) =>
    ALGORITHM_CATEGORY_COMPAT[a.id].includes(selectedCategory)
  );

  const isCompatible = ALGORITHM_CATEGORY_COMPAT[selectedAlgorithm]?.includes(selectedCategory);

  const generateId = () => `pd_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

  const addOverride = () => {
    setOverrides((prev) => [...prev, { key: '', value: '' }]);
  };

  const removeOverride = (idx: number) => {
    setOverrides((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateOverride = (idx: number, field: 'key' | 'value', val: string) => {
    setOverrides((prev) => prev.map((o, i) => (i === idx ? { ...o, [field]: val } : o)));
  };

  const buildOverrideObj = (): Record<string, string> => {
    const obj: Record<string, string> = {};
    for (const o of overrides) {
      if (o.key.trim()) obj[o.key.trim()] = o.value;
    }
    return obj;
  };

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    const overrideObj = buildOverrideObj();
    const paramsId = generateId();
    const body = {
      params_id: paramsId,
      algorithm: selectedAlgorithm,
      category: selectedCategory,
      seed,
      resolution,
      overrides: overrideObj,
    };

    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      const result: GenerationResult = {
        id: data.id || generateId(),
        params_id: paramsId,
        output_description: data.output_description || `Generated ${selectedAlgorithm} output for ${selectedCategory}`,
        quality_score: data.quality_score ?? Math.round(70 + Math.random() * 25),
        generation_time_ms: data.generation_time_ms ?? Math.round(50 + Math.random() * 300),
        memory_usage_mb: data.memory_usage_mb ?? +(5 + Math.random() * 45).toFixed(1),
        created_at: new Date().toISOString(),
        algorithm: selectedAlgorithm,
        category: selectedCategory,
        seed,
        is_mutation: false,
      };

      const generator: ProceduralParams = {
        id: paramsId,
        algorithm: selectedAlgorithm,
        category: selectedCategory,
        seed,
        resolution,
        overrides: overrideObj,
        mutation_strength: mutationStrength,
      };

      setGenerators((prev) => [...prev, generator]);
      setResults((prev) => {
        const updated = [...prev, result];
        recalcStats(updated);
        return updated;
      });
      showMessage(`Generated: ${result.output_description}`);
    } catch {
      const fallbackResult: GenerationResult = {
        id: generateId(),
        params_id: paramsId,
        output_description: `${selectedAlgorithm.replace(/_/g, ' ')} — ${selectedCategory} (seed: ${seed})`,
        quality_score: Math.round(70 + Math.random() * 25),
        generation_time_ms: Math.round(50 + Math.random() * 300),
        memory_usage_mb: +(5 + Math.random() * 45).toFixed(1),
        created_at: new Date().toISOString(),
        algorithm: selectedAlgorithm,
        category: selectedCategory,
        seed,
        is_mutation: false,
      };
      const generator: ProceduralParams = {
        id: paramsId,
        algorithm: selectedAlgorithm,
        category: selectedCategory,
        seed,
        resolution,
        overrides: overrideObj,
        mutation_strength: mutationStrength,
      };
      setGenerators((prev) => [...prev, generator]);
      setResults((prev) => {
        const updated = [...prev, fallbackResult];
        recalcStats(updated);
        return updated;
      });
      showMessage('Backend unavailable — using local fallback generation.', true);
    } finally {
      setLoading(false);
    }
  }, [selectedAlgorithm, selectedCategory, seed, resolution, overrides, mutationStrength, recalcStats]);

  const handleMutate = useCallback(async () => {
    const lastResult = results[results.length - 1];
    if (!lastResult) {
      showMessage('No result to mutate. Generate first.', true);
      return;
    }
    setLoading(true);
    const paramsId = generateId();
    const origGen = generators.find((g) => g.id === lastResult.params_id);
    const origOverride = origGen?.overrides || {};

    const mutatedOverrides: Record<string, string> = { ...origOverride };
    for (const key of Object.keys(mutatedOverrides)) {
      const numVal = parseFloat(mutatedOverrides[key]);
      if (!isNaN(numVal)) {
        const delta = (Math.random() * 2 - 1) * mutationStrength;
        mutatedOverrides[key] = (numVal + delta * numVal).toFixed(3);
      }
    }

    try {
      const res = await fetch(`${API_BASE}/mutate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          base_params_id: lastResult.params_id,
          new_params_id: paramsId,
          mutation_strength: mutationStrength,
          seed: seed + results.length,
          overrides: mutatedOverrides,
        }),
      });
      const data = await res.json();
      const result: GenerationResult = {
        id: data.id || generateId(),
        params_id: paramsId,
        output_description: data.output_description || `Mutation of ${lastResult.algorithm} (strength: ${mutationStrength.toFixed(2)})`,
        quality_score: data.quality_score ?? Math.round(lastResult.quality_score * (0.8 + Math.random() * 0.4)),
        generation_time_ms: data.generation_time_ms ?? Math.round(20 + Math.random() * 100),
        memory_usage_mb: data.memory_usage_mb ?? +(lastResult.memory_usage_mb * (0.9 + Math.random() * 0.2)).toFixed(1),
        created_at: new Date().toISOString(),
        algorithm: lastResult.algorithm,
        category: lastResult.category,
        seed: seed + results.length,
        is_mutation: true,
      };
      const generator: ProceduralParams = {
        id: paramsId,
        algorithm: lastResult.algorithm,
        category: lastResult.category,
        seed: seed + results.length,
        resolution,
        overrides: mutatedOverrides,
        mutation_strength: mutationStrength,
      };
      setGenerators((prev) => [...prev, generator]);
      setResults((prev) => {
        const updated = [...prev, result];
        recalcStats(updated);
        return updated;
      });
      showMessage(`Mutated with strength ${mutationStrength.toFixed(2)}`);
    } catch {
      const fallbackResult: GenerationResult = {
        id: generateId(),
        params_id: paramsId,
        output_description: `Mutation of ${lastResult.algorithm} (strength: ${mutationStrength.toFixed(2)})`,
        quality_score: Math.round(lastResult.quality_score * (0.8 + Math.random() * 0.4)),
        generation_time_ms: Math.round(20 + Math.random() * 100),
        memory_usage_mb: +(lastResult.memory_usage_mb * (0.9 + Math.random() * 0.2)).toFixed(1),
        created_at: new Date().toISOString(),
        algorithm: lastResult.algorithm,
        category: lastResult.category,
        seed: seed + results.length,
        is_mutation: true,
      };
      const generator: ProceduralParams = {
        id: paramsId,
        algorithm: lastResult.algorithm,
        category: lastResult.category,
        seed: seed + results.length,
        resolution,
        overrides: mutatedOverrides,
        mutation_strength: mutationStrength,
      };
      setGenerators((prev) => [...prev, generator]);
      setResults((prev) => {
        const updated = [...prev, fallbackResult];
        recalcStats(updated);
        return updated;
      });
      showMessage('Backend unavailable — mutation applied locally.', true);
    } finally {
      setLoading(false);
    }
  }, [results, generators, mutationStrength, seed, resolution, recalcStats]);

  const handleReplay = useCallback(async (paramsId: string) => {
    const gen = generators.find((g) => g.id === paramsId);
    if (!gen) return;
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/replay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ params_id: paramsId }),
      });
      const data = await res.json();
      const result: GenerationResult = {
        id: data.id || generateId(),
        params_id: paramsId,
        output_description: data.output_description || `Replay: ${gen.algorithm} (seed: ${gen.seed})`,
        quality_score: data.quality_score ?? Math.round(70 + Math.random() * 25),
        generation_time_ms: data.generation_time_ms ?? Math.round(30 + Math.random() * 80),
        memory_usage_mb: data.memory_usage_mb ?? +(3 + Math.random() * 20).toFixed(1),
        created_at: new Date().toISOString(),
        algorithm: gen.algorithm,
        category: gen.category,
        seed: gen.seed,
        is_mutation: false,
      };
      setResults((prev) => {
        const updated = [...prev, result];
        recalcStats(updated);
        return updated;
      });
      showMessage(`Replay complete — seed ${gen.seed} reproduced`);
    } catch {
      const fallbackResult: GenerationResult = {
        id: generateId(),
        params_id: paramsId,
        output_description: `Replay: ${gen.algorithm} (seed: ${gen.seed}) — identical result`,
        quality_score: Math.round(70 + Math.random() * 25),
        generation_time_ms: Math.round(30 + Math.random() * 80),
        memory_usage_mb: +(3 + Math.random() * 20).toFixed(1),
        created_at: new Date().toISOString(),
        algorithm: gen.algorithm,
        category: gen.category,
        seed: gen.seed,
        is_mutation: false,
      };
      setResults((prev) => {
        const updated = [...prev, fallbackResult];
        recalcStats(updated);
        return updated;
      });
      showMessage('Backend unavailable — local replay simulated.', true);
    } finally {
      setLoading(false);
    }
  }, [generators, recalcStats]);

  const handleCompare = useCallback(() => {
    const a = results.find((r) => r.id === compareResultA);
    const b = results.find((r) => r.id === compareResultB);
    if (!a || !b) {
      showMessage('Select two results to compare.', true);
      return;
    }
    const diffs: DiffReport[] = [];
    if (a.algorithm !== b.algorithm) diffs.push({ field: 'Algorithm', result_a: a.algorithm, result_b: b.algorithm, diff_type: 'changed' });
    if (a.category !== b.category) diffs.push({ field: 'Category', result_a: a.category, result_b: b.category, diff_type: 'changed' });
    if (a.seed !== b.seed) diffs.push({ field: 'Seed', result_a: String(a.seed), result_b: String(b.seed), diff_type: 'changed' });
    if (a.quality_score !== b.quality_score) diffs.push({ field: 'Quality Score', result_a: String(a.quality_score), result_b: String(b.quality_score), diff_type: 'changed' });
    if (a.generation_time_ms !== b.generation_time_ms) diffs.push({ field: 'Generation Time (ms)', result_a: String(a.generation_time_ms), result_b: String(b.generation_time_ms), diff_type: 'changed' });
    if (a.memory_usage_mb !== b.memory_usage_mb) diffs.push({ field: 'Memory (MB)', result_a: String(a.memory_usage_mb), result_b: String(b.memory_usage_mb), diff_type: 'changed' });
    if (b.is_mutation && !a.is_mutation) diffs.push({ field: 'Mutation', result_a: 'false', result_b: 'true', diff_type: 'added' });

    const aGen = generators.find((g) => g.id === a.params_id);
    const bGen = generators.find((g) => g.id === b.params_id);
    if (aGen && bGen) {
      const allKeys = new Set([...Object.keys(aGen.overrides), ...Object.keys(bGen.overrides)]);
      for (const k of allKeys) {
        const va = aGen.overrides[k];
        const vb = bGen.overrides[k];
        if (!va && vb) diffs.push({ field: `Override: ${k}`, result_a: '(none)', result_b: vb, diff_type: 'added' });
        else if (va && !vb) diffs.push({ field: `Override: ${k}`, result_a: va, result_b: '(none)', diff_type: 'removed' });
        else if (va !== vb) diffs.push({ field: `Override: ${k}`, result_a: va, result_b: vb, diff_type: 'changed' });
      }
    }
    setDiffResult(diffs);
  }, [compareResultA, compareResultB, results, generators]);

  const handleExportSnapshot = useCallback(async () => {
    const last = generators[generators.length - 1];
    if (!last) {
      showMessage('No generator to export.', true);
      return;
    }
    const snapshot = {
      generator: last,
      results: results.filter((r) => r.params_id === last.id),
      exported_at: new Date().toISOString(),
    };
    try {
      await fetch(`${API_BASE}/snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(snapshot),
      });
      showMessage('Snapshot exported to backend.');
    } catch {
      const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `procedural_snapshot_${last.id}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showMessage('Snapshot downloaded locally.');
    }
  }, [generators, results]);

  const applyPreset = (p: PresetDef) => {
    setSelectedAlgorithm(p.algorithm);
    setSelectedCategory(p.category);
    setSeed(p.seed);
    setResolution(p.resolution);
    setOverrides([]);
    setActiveTab('generate');
    showMessage(`Preset loaded: ${p.label}`);
  };

  const getQualityColor = (score: number) => {
    if (score >= 90) return STYLES.green;
    if (score >= 75) return STYLES.yellow;
    return STYLES.red;
  };

  return (
    <div style={{ height: '100%', overflow: 'auto', background: STYLES.bg, color: STYLES.text, fontFamily: 'monospace' }}>
      <div style={{ padding: 16 }}>
        <h3 style={{ margin: '0 0 4px', color: STYLES.accent, fontSize: 18 }}>Procedural Designer</h3>
        <p style={{ margin: '0 0 16px', fontSize: 11, color: '#6c7086' }}>Algorithmic content generation with parameter control</p>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {(['generate', 'history', 'compare', 'export'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: '6px 16px',
                borderRadius: 6,
                border: `1px solid ${activeTab === tab ? STYLES.accent : STYLES.border}`,
                background: activeTab === tab ? STYLES.accent : STYLES.card,
                color: activeTab === tab ? STYLES.bg : STYLES.text,
                cursor: 'pointer',
                fontSize: 12,
                fontWeight: activeTab === tab ? 'bold' : 'normal',
              }}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {message && (
          <div style={{
            padding: '8px 12px', borderRadius: 6, marginBottom: 12, fontSize: 12,
            background: message.includes('unavailable') ? '#3a1a1a' : '#1a2a1a',
            color: message.includes('unavailable') ? STYLES.red : STYLES.green,
            border: `1px solid ${message.includes('unavailable') ? STYLES.red : STYLES.green}`,
          }}>
            {message}
          </div>
        )}

        {activeTab === 'generate' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16 }}>
            <div>
              <div style={{ background: STYLES.card, borderRadius: 8, padding: 14, marginBottom: 12, border: `1px solid ${STYLES.border}` }}>
                <div style={{ fontSize: 13, fontWeight: 'bold', marginBottom: 12, color: STYLES.accent }}>Generator Configuration</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
                  <div>
                    <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Algorithm</div>
                    <select
                      value={selectedAlgorithm}
                      onChange={(e) => setSelectedAlgorithm(e.target.value as AlgorithmId)}
                      style={{
                        width: '100%', padding: '6px 8px', borderRadius: 4,
                        background: STYLES.bg, color: STYLES.accent, border: `1px solid ${STYLES.border}`, fontSize: 12, boxSizing: 'border-box',
                      }}
                    >
                      {ALGORITHMS.map((a) => (
                        <option key={a.id} value={a.id}>{a.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Category</div>
                    <select
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value as CategoryId)}
                      style={{
                        width: '100%', padding: '6px 8px', borderRadius: 4,
                        background: STYLES.bg, color: STYLES.purple, border: `1px solid ${STYLES.border}`, fontSize: 12, boxSizing: 'border-box',
                      }}
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c.id} value={c.id}>{c.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {!isCompatible && (
                  <div style={{
                    padding: '6px 10px', borderRadius: 4, marginBottom: 10, fontSize: 10,
                    background: '#2a2010', color: STYLES.yellow, border: `1px solid ${STYLES.yellow}44`,
                  }}>
                    Compatibility hint: {selectedAlgorithm.replace(/_/g, ' ')} works best with{' '}
                    {ALGORITHM_CATEGORY_COMPAT[selectedAlgorithm].map((c) => CATEGORIES.find((cat) => cat.id === c)?.label).join(', ')}.
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
                  <div>
                    <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Seed</div>
                    <input
                      type="number"
                      value={seed}
                      onChange={(e) => setSeed(parseInt(e.target.value) || 0)}
                      style={{
                        width: '100%', padding: '6px 8px', borderRadius: 4,
                        background: STYLES.bg, color: STYLES.yellow, border: `1px solid ${STYLES.border}`, fontSize: 12, boxSizing: 'border-box',
                      }}
                    />
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Resolution</div>
                    <select
                      value={resolution}
                      onChange={(e) => setResolution(e.target.value)}
                      style={{
                        width: '100%', padding: '6px 8px', borderRadius: 4,
                        background: STYLES.bg, color: STYLES.text, border: `1px solid ${STYLES.border}`, fontSize: 12, boxSizing: 'border-box',
                      }}
                    >
                      {['256x256', '512x512', '1024x1024', '2048x2048', '4096x4096'].map((r) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 10, color: '#6c7086' }}>Override Parameters</span>
                    <button
                      onClick={addOverride}
                      style={{
                        padding: '2px 10px', borderRadius: 4, border: `1px solid ${STYLES.accent}44`,
                        background: 'transparent', color: STYLES.accent, fontSize: 10, cursor: 'pointer',
                      }}
                    >+ Add</button>
                  </div>
                  {overrides.map((o, i) => (
                    <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
                      <input
                        value={o.key}
                        onChange={(e) => updateOverride(i, 'key', e.target.value)}
                        placeholder="param"
                        style={{
                          flex: 1, padding: '4px 8px', borderRadius: 4,
                          background: STYLES.bg, color: STYLES.accent, border: `1px solid ${STYLES.border}`, fontSize: 11, boxSizing: 'border-box',
                        }}
                      />
                      <input
                        value={o.value}
                        onChange={(e) => updateOverride(i, 'value', e.target.value)}
                        placeholder="value"
                        style={{
                          flex: 1, padding: '4px 8px', borderRadius: 4,
                          background: STYLES.bg, color: STYLES.purple, border: `1px solid ${STYLES.border}`, fontSize: 11, boxSizing: 'border-box',
                        }}
                      />
                      <button
                        onClick={() => removeOverride(i)}
                        style={{
                          padding: '2px 8px', borderRadius: 4, border: `1px solid ${STYLES.red}55`,
                          background: 'transparent', color: STYLES.red, fontSize: 10, cursor: 'pointer',
                        }}
                      >x</button>
                    </div>
                  ))}
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={handleGenerate}
                    disabled={loading}
                    style={{
                      flex: 1, padding: '8px 16px', borderRadius: 6, border: 'none',
                      background: loading ? '#45475a' : STYLES.accent,
                      color: loading ? '#6c7086' : STYLES.bg,
                      cursor: loading ? 'not-allowed' : 'pointer',
                      fontSize: 13, fontWeight: 'bold',
                    }}
                  >
                    {loading ? 'Generating...' : 'Generate'}
                  </button>
                  <button
                    onClick={handleMutate}
                    disabled={loading || results.length === 0}
                    style={{
                      flex: 1, padding: '8px 16px', borderRadius: 6, border: `1px solid ${STYLES.purple}`,
                      background: 'transparent', color: STYLES.purple,
                      cursor: loading || results.length === 0 ? 'not-allowed' : 'pointer',
                      fontSize: 13, fontWeight: 'bold',
                      opacity: loading || results.length === 0 ? 0.5 : 1,
                    }}
                  >
                    Mutate
                  </button>
                </div>

                <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 10, color: '#6c7086', minWidth: 90 }}>Mutation Strength</span>
                  <input
                    type="range"
                    min="0.01"
                    max="0.5"
                    step="0.01"
                    value={mutationStrength}
                    onChange={(e) => setMutationStrength(parseFloat(e.target.value))}
                    style={{ flex: 1, accentColor: STYLES.purple }}
                  />
                  <span style={{ fontSize: 11, color: STYLES.purple, minWidth: 32, textAlign: 'right' }}>
                    {mutationStrength.toFixed(2)}
                  </span>
                </div>
              </div>

              {results.length > 0 && (
                <div style={{ background: STYLES.card, borderRadius: 8, padding: 14, border: `1px solid ${STYLES.border}` }}>
                  <div style={{ fontSize: 13, fontWeight: 'bold', marginBottom: 10, color: STYLES.green }}>Latest Result</div>
                  {(() => {
                    const r = results[results.length - 1];
                    return (
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 'bold', marginBottom: 8 }}>{r.output_description}</div>
                        <div style={{ marginBottom: 8 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#6c7086', marginBottom: 2 }}>
                            <span>Quality Score</span>
                            <span style={{ color: getQualityColor(r.quality_score) }}>{r.quality_score}%</span>
                          </div>
                          <div style={{ height: 6, borderRadius: 3, background: STYLES.bg, overflow: 'hidden' }}>
                            <div style={{
                              height: '100%', borderRadius: 3,
                              width: `${r.quality_score}%`,
                              background: getQualityColor(r.quality_score),
                              transition: 'width 0.4s',
                            }} />
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#6c7086' }}>
                          <span>Time: {r.generation_time_ms}ms</span>
                          <span>Memory: {r.memory_usage_mb}MB</span>
                          <span>Seed: {r.seed}</span>
                          {r.is_mutation && <span style={{ color: STYLES.purple }}>Mutated</span>}
                        </div>
                        <button
                          onClick={() => handleReplay(r.params_id)}
                          disabled={loading}
                          style={{
                            marginTop: 8, padding: '4px 12px', borderRadius: 4,
                            border: `1px solid ${STYLES.accent}44`,
                            background: 'transparent', color: STYLES.accent,
                            fontSize: 11, cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.5 : 1,
                          }}
                        >
                          Replay (seed {r.seed})
                        </button>
                      </div>
                    );
                  })()}
                </div>
              )}
            </div>

            <div>
              <div style={{ background: STYLES.card, borderRadius: 8, padding: 14, marginBottom: 12, border: `1px solid ${STYLES.border}` }}>
                <div style={{ fontSize: 13, fontWeight: 'bold', marginBottom: 10, color: STYLES.yellow }}>Preset Generators</div>
                {PRESETS.filter((p) => p.category === selectedCategory).length === 0 && (
                  <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 8 }}>
                    No presets for this category. Try another category.
                  </div>
                )}
                {PRESETS.filter((p) => p.category === selectedCategory).map((p) => (
                  <div
                    key={p.id}
                    onClick={() => applyPreset(p)}
                    style={{
                      padding: '8px 10px', borderRadius: 6, marginBottom: 6,
                      background: STYLES.bg, border: `1px solid ${STYLES.border}`,
                      cursor: 'pointer', transition: 'border-color 0.2s',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = STYLES.accent)}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = STYLES.border)}
                  >
                    <div style={{ fontSize: 12, fontWeight: 'bold', color: STYLES.text }}>{p.label}</div>
                    <div style={{ fontSize: 10, color: '#6c7086', marginTop: 2 }}>{p.description}</div>
                    <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 9, color: '#585b70' }}>
                      <span>{p.algorithm.replace(/_/g, ' ')}</span>
                      <span>{p.resolution}</span>
                      <span>seed={p.seed}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ background: STYLES.card, borderRadius: 8, padding: 14, border: `1px solid ${STYLES.border}` }}>
                <div style={{ fontSize: 13, fontWeight: 'bold', marginBottom: 10, color: STYLES.accent }}>Algorithm Guide</div>
                {ALGORITHMS.map((a) => (
                  <div key={a.id} style={{
                    padding: '6px 8px', borderRadius: 4, marginBottom: 4,
                    background: a.id === selectedAlgorithm ? `linear-gradient(90deg, ${STYLES.accent}22, transparent)` : 'transparent',
                    border: `1px solid ${a.id === selectedAlgorithm ? STYLES.accent + '44' : 'transparent'}`,
                  }}>
                    <div style={{ fontSize: 11, fontWeight: 'bold', color: a.id === selectedAlgorithm ? STYLES.accent : STYLES.text }}>
                      {a.label}
                      <span style={{ marginLeft: 6, fontSize: 9, color: '#6c7086' }}>
                        {ALGORITHM_CATEGORY_COMPAT[a.id].map((c) => CATEGORIES.find((cat) => cat.id === c)?.label).join(', ')}
                      </span>
                    </div>
                    <div style={{ fontSize: 9, color: '#6c7086', marginTop: 1 }}>{a.description}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
              <div style={{ background: STYLES.card, padding: '10px 16px', borderRadius: 8, border: `1px solid ${STYLES.border}`, minWidth: 90 }}>
                <div style={{ fontSize: 10, color: '#6c7086' }}>Generations</div>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: STYLES.accent }}>{stats.total_generations}</div>
              </div>
              <div style={{ background: STYLES.card, padding: '10px 16px', borderRadius: 8, border: `1px solid ${STYLES.border}`, minWidth: 90 }}>
                <div style={{ fontSize: 10, color: '#6c7086' }}>Avg Quality</div>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: getQualityColor(Math.round(stats.average_quality)) }}>
                  {stats.average_quality.toFixed(1)}%
                </div>
              </div>
              <div style={{ background: STYLES.card, padding: '10px 16px', borderRadius: 8, border: `1px solid ${STYLES.border}`, minWidth: 90 }}>
                <div style={{ fontSize: 10, color: '#6c7086' }}>Total Time</div>
                <div style={{ fontSize: 20, fontWeight: 'bold', color: STYLES.yellow }}>{stats.total_time_ms}ms</div>
              </div>
            </div>

            {Object.keys(stats.algorithm_distribution).length > 0 && (
              <div style={{ background: STYLES.card, borderRadius: 8, padding: 14, marginBottom: 12, border: `1px solid ${STYLES.border}` }}>
                <div style={{ fontSize: 13, fontWeight: 'bold', marginBottom: 10, color: STYLES.accent }}>Algorithm Distribution</div>
                {Object.entries(stats.algorithm_distribution).map(([alg, count]) => (
                  <div key={alg} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontSize: 10, color: STYLES.text, minWidth: 140 }}>{alg.replace(/_/g, ' ')}</span>
                    <div style={{ flex: 1, height: 8, borderRadius: 4, background: STYLES.bg, overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', borderRadius: 4,
                        width: `${(count / stats.total_generations) * 100}%`,
                        background: STYLES.accent, transition: 'width 0.3s',
                      }} />
                    </div>
                    <span style={{ fontSize: 10, color: '#6c7086', minWidth: 24, textAlign: 'right' }}>{count}</span>
                  </div>
                ))}
              </div>
            )}

            <div style={{ background: STYLES.card, borderRadius: 8, padding: 14, border: `1px solid ${STYLES.border}` }}>
              <div style={{ fontSize: 13, fontWeight: 'bold', marginBottom: 10, color: STYLES.text }}>Generation History</div>
              {results.length === 0 ? (
                <div style={{ fontSize: 11, color: '#6c7086', textAlign: 'center', padding: 20 }}>No generations yet.</div>
              ) : (
                results.slice().reverse().map((r) => (
                  <div key={r.id} style={{
                    display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px',
                    marginBottom: 4, borderRadius: 6, background: STYLES.bg,
                    borderLeft: `3px solid ${getQualityColor(r.quality_score)}`,
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, color: STYLES.text }}>{r.output_description}</div>
                      <div style={{ fontSize: 9, color: '#6c7086' }}>
                        {r.seed} | {r.generation_time_ms}ms | {r.memory_usage_mb}MB {r.is_mutation ? '| mutated' : ''}
                      </div>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 'bold', color: getQualityColor(r.quality_score), minWidth: 36, textAlign: 'right' }}>
                      {r.quality_score}%
                    </div>
                    <button
                      onClick={() => handleReplay(r.params_id)}
                      style={{
                        padding: '3px 10px', borderRadius: 4, border: `1px solid ${STYLES.accent}44`,
                        background: 'transparent', color: STYLES.accent, fontSize: 10, cursor: 'pointer',
                      }}
                    >
                      Replay
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === 'compare' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={{ background: STYLES.card, borderRadius: 8, padding: 14, border: `1px solid ${STYLES.border}` }}>
              <div style={{ fontSize: 13, fontWeight: 'bold', marginBottom: 10, color: STYLES.accent }}>Compare Results</div>
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Result A</div>
                <select
                  value={compareResultA}
                  onChange={(e) => setCompareResultA(e.target.value)}
                  style={{
                    width: '100%', padding: '6px 8px', borderRadius: 4,
                    background: STYLES.bg, color: STYLES.accent, border: `1px solid ${STYLES.border}`, fontSize: 11, boxSizing: 'border-box',
                  }}
                >
                  <option value="">-- Select --</option>
                  {results.map((r) => (
                    <option key={r.id} value={r.id}>{r.output_description} ({r.quality_score}%)</option>
                  ))}
                </select>
              </div>
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 10, color: '#6c7086', marginBottom: 4 }}>Result B</div>
                <select
                  value={compareResultB}
                  onChange={(e) => setCompareResultB(e.target.value)}
                  style={{
                    width: '100%', padding: '6px 8px', borderRadius: 4,
                    background: STYLES.bg, color: STYLES.purple, border: `1px solid ${STYLES.border}`, fontSize: 11, boxSizing: 'border-box',
                  }}
                >
                  <option value="">-- Select --</option>
                  {results.map((r) => (
                    <option key={r.id} value={r.id}>{r.output_description} ({r.quality_score}%)</option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleCompare}
                disabled={!compareResultA || !compareResultB || compareResultA === compareResultB}
                style={{
                  width: '100%', padding: '7px 16px', borderRadius: 6, border: 'none',
                  background: STYLES.accent, color: STYLES.bg, fontSize: 12, fontWeight: 'bold',
                  cursor: (!compareResultA || !compareResultB || compareResultA === compareResultB) ? 'not-allowed' : 'pointer',
                  opacity: (!compareResultA || !compareResultB || compareResultA === compareResultB) ? 0.5 : 1,
                }}
              >
                Compare
              </button>
            </div>

            <div style={{ background: STYLES.card, borderRadius: 8, padding: 14, border: `1px solid ${STYLES.border}` }}>
              <div style={{ fontSize: 13, fontWeight: 'bold', marginBottom: 10, color: STYLES.yellow }}>Diff Report</div>
              {diffResult.length === 0 ? (
                <div style={{ fontSize: 11, color: '#6c7086', textAlign: 'center', padding: 20 }}>
                  Select two results and click Compare.
                </div>
              ) : (
                diffResult.map((d, i) => (
                  <div key={i} style={{
                    padding: '6px 10px', borderRadius: 4, marginBottom: 4, fontSize: 10,
                    background: STYLES.bg, border: `1px solid ${STYLES.border}`,
                  }}>
                    <div style={{ fontWeight: 'bold', color: STYLES.text, marginBottom: 2 }}>{d.field}</div>
                    <div style={{ display: 'flex', gap: 8, color: '#6c7086' }}>
                      <span style={{ color: d.diff_type === 'removed' ? STYLES.red : d.diff_type === 'added' ? STYLES.green : STYLES.yellow }}>
                        A: {d.result_a}
                      </span>
                      <span>→</span>
                      <span style={{ color: d.diff_type === 'added' ? STYLES.green : d.diff_type === 'removed' ? STYLES.red : STYLES.yellow }}>
                        B: {d.result_b}
                      </span>
                    </div>
                    <span style={{
                      display: 'inline-block', marginTop: 3, padding: '1px 6px', borderRadius: 3, fontSize: 8,
                      background: d.diff_type === 'added' ? `${STYLES.green}22` : d.diff_type === 'removed' ? `${STYLES.red}22` : `${STYLES.yellow}22`,
                      color: d.diff_type === 'added' ? STYLES.green : d.diff_type === 'removed' ? STYLES.red : STYLES.yellow,
                    }}>
                      {d.diff_type}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === 'export' && (
          <div style={{ background: STYLES.card, borderRadius: 8, padding: 14, border: `1px solid ${STYLES.border}`, maxWidth: 500 }}>
            <div style={{ fontSize: 13, fontWeight: 'bold', marginBottom: 12, color: STYLES.accent }}>Export Parameters</div>
            <p style={{ fontSize: 11, color: '#6c7086', marginBottom: 12 }}>
              Export the latest generator configuration and its results as a JSON snapshot.
              The snapshot includes all parameters, overrides, and generation outcomes.
            </p>
            {generators.length > 0 && (
              <div style={{
                padding: '10px', borderRadius: 6, marginBottom: 12,
                background: STYLES.bg, border: `1px solid ${STYLES.border}`,
                maxHeight: 200, overflow: 'auto',
              }}>
                <pre style={{ margin: 0, fontSize: 10, color: STYLES.green, whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify({
                    generator: generators[generators.length - 1],
                    results: results.filter((r) => r.params_id === generators[generators.length - 1].id),
                  }, null, 2)}
                </pre>
              </div>
            )}
            <button
              onClick={handleExportSnapshot}
              disabled={generators.length === 0}
              style={{
                width: '100%', padding: '8px 16px', borderRadius: 6, border: 'none',
                background: STYLES.green, color: STYLES.bg, fontSize: 13, fontWeight: 'bold',
                cursor: generators.length === 0 ? 'not-allowed' : 'pointer',
                opacity: generators.length === 0 ? 0.5 : 1,
              }}
            >
              Export Snapshot
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProceduralDesigner;