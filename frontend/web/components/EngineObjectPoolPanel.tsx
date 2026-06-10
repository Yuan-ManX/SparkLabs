import React, { useState, useEffect, useCallback } from 'react';

type ActiveTab = 'pool-manager' | 'borrow-return' | 'optimization' | 'status';

interface PoolInfo {
  id: string;
  pool_name: string;
  object_type: string;
  total: number;
  available: number;
  in_use: number;
  peak_usage: number;
}

interface PoolStatus {
  total_pools: number;
  total_objects: number;
  total_in_use: number;
  total_available: number;
  total_memory_estimate_bytes: number;
  pools: PoolInfo[];
}

interface BorrowResult {
  object_id: string;
  pool_id: string;
  object_type: string;
  properties: Record<string, unknown>;
}

interface OptimizationResult {
  pools_adjusted: number;
  objects_created: number;
  objects_destroyed: number;
  memory_savings: number;
}

interface PredictDemandResult {
  pool_id: string;
  predicted_demand: number;
  time_window_seconds: number;
  confidence: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const defaultPools: PoolInfo[] = [
  { id: uid(), pool_name: 'EntityPool', object_type: 'GameEntity', total: 500, available: 320, in_use: 180, peak_usage: 250 },
  { id: uid(), pool_name: 'ProjectilePool', object_type: 'Projectile', total: 1000, available: 750, in_use: 250, peak_usage: 400 },
  { id: uid(), pool_name: 'ParticlePool', object_type: 'Particle', total: 2000, available: 1200, in_use: 800, peak_usage: 1500 },
];

const EngineObjectPoolPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('pool-manager');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<PoolStatus | null>(null);
  const [pools, setPools] = useState<PoolInfo[]>(defaultPools);

  // Pool Manager form
  const [poolForm, setPoolForm] = useState({
    poolName: '',
    objectType: '',
    strategy: 'fixed_size',
    initialSize: 100,
    maxSize: 1000,
    growthFactor: 1.5,
    allocationPolicy: 'round_robin',
  });

  // Prewarm form
  const [prewarmForm, setPrewarmForm] = useState({ poolId: '', count: 50, background: true });

  // Borrow/Return
  const [borrowPoolId, setBorrowPoolId] = useState('');
  const [requiredProperties, setRequiredProperties] = useState('{}');
  const [borrowResult, setBorrowResult] = useState<BorrowResult | null>(null);
  const [returnObjectId, setReturnObjectId] = useState('');

  // Optimization
  const [optimizationPoolId, setOptimizationPoolId] = useState('');
  const [timeWindowSeconds, setTimeWindowSeconds] = useState(60);
  const [predictResult, setPredictResult] = useState<PredictDemandResult | null>(null);
  const [optimizationResult, setOptimizationResult] = useState<OptimizationResult | null>(null);

  const apiBase = 'http://localhost:8000/api/engine';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/object-pool/status`);
      if (!res.ok) throw new Error('Failed to fetch status');
      const data: PoolStatus = await res.json();
      setStatus(data);
      if (data.pools && data.pools.length > 0) {
        setPools(data.pools);
      }
    } catch {
      // Use default data on failure
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (activeTab !== 'status') return;
    const interval = setInterval(() => fetchStatus(), 15000);
    return () => clearInterval(interval);
  }, [activeTab, fetchStatus]);

  const handleCreatePool = async () => {
    if (!poolForm.poolName.trim()) { showMessage('Please enter a pool name', 'error'); return; }
    if (!poolForm.objectType.trim()) { showMessage('Please enter an object type', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/object-pool/create-pool`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pool_name: poolForm.poolName,
          object_type: poolForm.objectType,
          strategy: poolForm.strategy,
          initial_size: poolForm.initialSize,
          max_size: poolForm.maxSize,
          growth_factor: poolForm.growthFactor,
          allocation_policy: poolForm.allocationPolicy,
        }),
      });
      if (!res.ok) throw new Error('Pool creation failed');
      const data = await res.json();
      const newPool: PoolInfo = {
        id: data.id || uid(),
        pool_name: poolForm.poolName,
        object_type: poolForm.objectType,
        total: poolForm.initialSize,
        available: poolForm.initialSize,
        in_use: 0,
        peak_usage: 0,
      };
      setPools(prev => [newPool, ...prev]);
      showMessage('Pool created', 'success');
      fetchStatus();
    } catch {
      const newPool: PoolInfo = {
        id: uid(),
        pool_name: poolForm.poolName,
        object_type: poolForm.objectType,
        total: poolForm.initialSize,
        available: poolForm.initialSize,
        in_use: 0,
        peak_usage: 0,
      };
      setPools(prev => [newPool, ...prev]);
      showMessage('Pool created (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handlePrewarm = async (poolId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/object-pool/prewarm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pool_id: poolId, count: prewarmForm.count, background: prewarmForm.background }),
      });
      if (!res.ok) throw new Error('Prewarm failed');
      showMessage('Pool prewarmed', 'success');
      fetchStatus();
    } catch {
      showMessage('Pool prewarmed (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleRecycle = async (poolId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/object-pool/recycle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pool_id: poolId }),
      });
      if (!res.ok) throw new Error('Recycle failed');
      showMessage('Pool recycled', 'success');
      fetchStatus();
    } catch {
      showMessage('Pool recycled (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleBorrow = async () => {
    if (!borrowPoolId) { showMessage('Please select a pool', 'error'); return; }
    let props: Record<string, unknown> = {};
    try {
      props = JSON.parse(requiredProperties);
    } catch {
      showMessage('Invalid JSON in required properties', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/object-pool/borrow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pool_id: borrowPoolId, required_properties: props }),
      });
      if (!res.ok) throw new Error('Borrow failed');
      const data: BorrowResult = await res.json();
      setBorrowResult(data);
      showMessage('Object borrowed', 'success');
      fetchStatus();
    } catch {
      const fallback: BorrowResult = {
        object_id: uid(),
        pool_id: borrowPoolId,
        object_type: pools.find(p => p.id === borrowPoolId)?.object_type || 'Unknown',
        properties: props,
      };
      setBorrowResult(fallback);
      showMessage('Object borrowed (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleReturn = async () => {
    if (!borrowPoolId) { showMessage('Please select a pool', 'error'); return; }
    if (!returnObjectId.trim()) { showMessage('Please enter an object ID', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/object-pool/return`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pool_id: borrowPoolId, object_id: returnObjectId }),
      });
      if (!res.ok) throw new Error('Return failed');
      showMessage('Object returned', 'success');
      setBorrowResult(null);
      setReturnObjectId('');
      fetchStatus();
    } catch {
      showMessage('Object returned (offline mode)', 'info');
      setBorrowResult(null);
      setReturnObjectId('');
    } finally {
      setLoading(false);
    }
  };

  const handleForceGC = async () => {
    if (!borrowPoolId) { showMessage('Please select a pool', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/object-pool/force-gc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pool_id: borrowPoolId }),
      });
      if (!res.ok) throw new Error('GC failed');
      showMessage('Garbage collection triggered', 'success');
      fetchStatus();
    } catch {
      showMessage('Garbage collection triggered (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handlePredictDemand = async () => {
    if (!optimizationPoolId) { showMessage('Please select a pool', 'error'); return; }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/object-pool/predict-demand`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pool_id: optimizationPoolId, time_window_seconds: timeWindowSeconds }),
      });
      if (!res.ok) throw new Error('Prediction failed');
      const data: PredictDemandResult = await res.json();
      setPredictResult(data);
      showMessage('Demand predicted', 'success');
    } catch {
      const fallback: PredictDemandResult = {
        pool_id: optimizationPoolId,
        predicted_demand: Math.floor(Math.random() * 500 + 100),
        time_window_seconds: timeWindowSeconds,
        confidence: Math.random() * 0.3 + 0.7,
      };
      setPredictResult(fallback);
      showMessage('Demand predicted (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleAutoOptimize = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/object-pool/auto-optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error('Auto-optimize failed');
      const data: OptimizationResult = await res.json();
      setOptimizationResult(data);
      showMessage('Auto-optimization complete', 'success');
      fetchStatus();
    } catch {
      const fallback: OptimizationResult = {
        pools_adjusted: 3,
        objects_created: 150,
        objects_destroyed: 80,
        memory_savings: 1024 * 512,
      };
      setOptimizationResult(fallback);
      showMessage('Auto-optimization complete (offline mode)', 'info');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await fetchStatus();
    showMessage('Panel refreshed', 'info');
  };

  const formatBytes = (bytes: number): string => {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '6px 8px',
    fontSize: 12,
    backgroundColor: '#1a1a2e',
    color: '#e0e0e0',
    border: '1px solid #0f3460',
    borderRadius: 4,
    boxSizing: 'border-box',
  };

  const tabItems: { key: ActiveTab; label: string; icon: string }[] = [
    { key: 'pool-manager', label: 'Pool Manager', icon: '\uD83D\uDDC2\uFE0F' },
    { key: 'borrow-return', label: 'Borrow/Return', icon: '\u21C4' },
    { key: 'optimization', label: 'Optimization', icon: '\u26A1' },
    { key: 'status', label: 'Status', icon: '\u2699\uFE0F' },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>{'\uD83D\uDDC2\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Engine Object Pool</span>
        </div>
        <button
          onClick={handleRefresh}
          style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}
        >
          {'\u21BB'} Refresh
        </button>
      </div>

      {/* Message banner */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #0f3460' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* ==================== POOL MANAGER TAB ==================== */}
        {activeTab === 'pool-manager' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Create Pool Form */}
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                Create Pool
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Pool Name</label>
                  <input
                    type="text" value={poolForm.poolName}
                    onChange={e => setPoolForm(prev => ({ ...prev, poolName: e.target.value }))}
                    placeholder="e.g. EntityPool" style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Object Type</label>
                  <input
                    type="text" value={poolForm.objectType}
                    onChange={e => setPoolForm(prev => ({ ...prev, objectType: e.target.value }))}
                    placeholder="e.g. GameEntity" style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Strategy</label>
                  <select
                    value={poolForm.strategy}
                    onChange={e => setPoolForm(prev => ({ ...prev, strategy: e.target.value }))}
                    style={inputStyle}
                  >
                    <option value="fixed_size">Fixed Size</option>
                    <option value="dynamic_growth">Dynamic Growth</option>
                    <option value="predictive">Predictive</option>
                    <option value="adaptive">Adaptive</option>
                    <option value="lazy">Lazy</option>
                    <option value="eager">Eager</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Allocation Policy</label>
                  <select
                    value={poolForm.allocationPolicy}
                    onChange={e => setPoolForm(prev => ({ ...prev, allocationPolicy: e.target.value }))}
                    style={inputStyle}
                  >
                    <option value="round_robin">Round Robin</option>
                    <option value="first_available">First Available</option>
                    <option value="least_used">Least Used</option>
                    <option value="random">Random</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Initial Size</label>
                  <input
                    type="number" value={poolForm.initialSize}
                    onChange={e => setPoolForm(prev => ({ ...prev, initialSize: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Max Size</label>
                  <input
                    type="number" value={poolForm.maxSize}
                    onChange={e => setPoolForm(prev => ({ ...prev, maxSize: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Growth Factor</label>
                  <input
                    type="number" value={poolForm.growthFactor}
                    onChange={e => setPoolForm(prev => ({ ...prev, growthFactor: parseFloat(e.target.value) || 0 }))}
                    step="0.1" style={inputStyle}
                  />
                </div>
              </div>
              <button
                onClick={handleCreatePool} disabled={loading}
                style={{
                  padding: '8px 18px', backgroundColor: '#0f3460', color: '#74b9ff',
                  border: '1px solid #1a5276', borderRadius: 4,
                  cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600,
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? 'Creating...' : '\uD83D\uDDC2\uFE0F Create Pool'}
              </button>
            </div>

            {/* Prewarm Controls */}
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                Prewarm Configuration
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 4 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Count</label>
                  <input
                    type="number" value={prewarmForm.count}
                    onChange={e => setPrewarmForm(prev => ({ ...prev, count: parseInt(e.target.value, 10) || 0 }))}
                    style={inputStyle}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Background</label>
                  <select
                    value={prewarmForm.background ? 'true' : 'false'}
                    onChange={e => setPrewarmForm(prev => ({ ...prev, background: e.target.value === 'true' }))}
                    style={inputStyle}
                  >
                    <option value="true">Yes</option>
                    <option value="false">No</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Current Pools List */}
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: -4, color: '#aaa' }}>
              Current Pools ({pools.length})
            </div>
            {pools.map(pool => (
              <div
                key={pool.id}
                style={{
                  padding: 12, backgroundColor: '#16213e', borderRadius: 8,
                  border: '1px solid #0f3460',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{pool.pool_name}</span>
                    <span style={{
                      marginLeft: 8, fontSize: 10, color: '#74b9ff',
                      backgroundColor: '#1a1a2e', padding: '2px 6px', borderRadius: 3,
                    }}>
                      {pool.object_type}
                    </span>
                  </div>
                  <span style={{ fontSize: 10, color: '#888' }}>ID: {pool.id.slice(0, 8)}</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Total</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{pool.total}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Available</div>
                    <div style={{ color: '#6bcb77', fontWeight: 600 }}>{pool.available}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>In Use</div>
                    <div style={{ color: '#fdcb6e', fontWeight: 600 }}>{pool.in_use}</div>
                  </div>
                  <div style={{ padding: '4px 6px', backgroundColor: '#1a1a2e', borderRadius: 4, textAlign: 'center', fontSize: 10 }}>
                    <div style={{ color: '#888' }}>Peak Usage</div>
                    <div style={{ color: '#ff6b6b', fontWeight: 600 }}>{pool.peak_usage}</div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    onClick={() => handlePrewarm(pool.id)}
                    disabled={loading}
                    style={{
                      padding: '5px 12px', backgroundColor: '#0f3460', color: '#fdcb6e',
                      border: '1px solid #1a5276', borderRadius: 4,
                      cursor: loading ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600,
                      opacity: loading ? 0.6 : 1,
                    }}
                  >
                    {'\u26A1'} Prewarm
                  </button>
                  <button
                    onClick={() => handleRecycle(pool.id)}
                    disabled={loading}
                    style={{
                      padding: '5px 12px', backgroundColor: '#0f3460', color: '#a29bfe',
                      border: '1px solid #1a5276', borderRadius: 4,
                      cursor: loading ? 'not-allowed' : 'pointer', fontSize: 11, fontWeight: 600,
                      opacity: loading ? 0.6 : 1,
                    }}
                  >
                    {'\u267B\uFE0F'} Recycle
                  </button>
                </div>
              </div>
            ))}

            {pools.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 30, color: '#555',
                backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460',
              }}>
                <span style={{ fontSize: 30, opacity: 0.3, display: 'block', marginBottom: 8 }}>{'\uD83D\uDDC2\uFE0F'}</span>
                No pools created yet. Use the form above to create your first pool.
              </div>
            )}
          </div>
        )}

        {/* ==================== BORROW / RETURN TAB ==================== */}
        {activeTab === 'borrow-return' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Borrow Object */}
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                Borrow Object
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Pool</label>
                  <select
                    value={borrowPoolId}
                    onChange={e => setBorrowPoolId(e.target.value)}
                    style={inputStyle}
                  >
                    <option value="">-- Select Pool --</option>
                    {pools.map(p => (
                      <option key={p.id} value={p.id}>{p.pool_name} ({p.object_type})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>
                    Required Properties (JSON)
                  </label>
                  <textarea
                    value={requiredProperties}
                    onChange={e => setRequiredProperties(e.target.value)}
                    placeholder='{"position": [0,0,0], "health": 100}'
                    rows={3}
                    style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace' }}
                  />
                </div>
              </div>
              <button
                onClick={handleBorrow} disabled={loading}
                style={{
                  padding: '8px 18px', backgroundColor: '#0f3460', color: '#6bcb77',
                  border: '1px solid #1a5276', borderRadius: 4,
                  cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600,
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? 'Borrowing...' : '\u21C4 Borrow Object'}
              </button>

              {borrowResult && (
                <div style={{
                  marginTop: 10, padding: 10, backgroundColor: '#1a1a2e',
                  borderRadius: 6, border: '1px solid #0f3460', fontSize: 11,
                }}>
                  <div style={{ fontWeight: 600, color: '#6bcb77', marginBottom: 6 }}>
                    Borrowed Object Details
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                    <div style={{ color: '#888' }}>Object ID:</div>
                    <div style={{ color: '#e0e0e0', fontFamily: 'monospace' }}>{borrowResult.object_id}</div>
                    <div style={{ color: '#888' }}>Object Type:</div>
                    <div style={{ color: '#e0e0e0' }}>{borrowResult.object_type}</div>
                    <div style={{ color: '#888' }}>Pool ID:</div>
                    <div style={{ color: '#e0e0e0', fontFamily: 'monospace' }}>{borrowResult.pool_id.slice(0, 12)}...</div>
                  </div>
                  <div style={{ marginTop: 6 }}>
                    <div style={{ color: '#888', marginBottom: 2 }}>Properties:</div>
                    <pre style={{
                      margin: 0, padding: '4px 6px', backgroundColor: '#141428',
                      borderRadius: 3, fontSize: 10, color: '#a29bfe',
                      overflow: 'auto', maxHeight: 100,
                    }}>
                      {JSON.stringify(borrowResult.properties, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>

            {/* Return Object */}
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                Return Object
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Pool</label>
                  <select
                    value={borrowPoolId}
                    onChange={e => setBorrowPoolId(e.target.value)}
                    style={inputStyle}
                  >
                    <option value="">-- Select Pool --</option>
                    {pools.map(p => (
                      <option key={p.id} value={p.id}>{p.pool_name} ({p.object_type})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Object ID</label>
                  <input
                    type="text" value={returnObjectId}
                    onChange={e => setReturnObjectId(e.target.value)}
                    placeholder="Enter object ID to return"
                    style={inputStyle}
                  />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={handleReturn} disabled={loading}
                  style={{
                    padding: '8px 18px', backgroundColor: '#0f3460', color: '#a29bfe',
                    border: '1px solid #1a5276', borderRadius: 4,
                    cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600,
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading ? 'Returning...' : '\u21A9\uFE0F Return Object'}
                </button>
                <button
                  onClick={handleForceGC} disabled={loading}
                  style={{
                    padding: '8px 18px', backgroundColor: '#0f3460', color: '#ff6b6b',
                    border: '1px solid #1a5276', borderRadius: 4,
                    cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600,
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading ? 'Running...' : '\uD83D\uDDD1\uFE0F GC'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ==================== OPTIMIZATION TAB ==================== */}
        {activeTab === 'optimization' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Predict Demand */}
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                Predict Demand
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>Pool</label>
                  <select
                    value={optimizationPoolId}
                    onChange={e => setOptimizationPoolId(e.target.value)}
                    style={inputStyle}
                  >
                    <option value="">-- Select Pool --</option>
                    {pools.map(p => (
                      <option key={p.id} value={p.id}>{p.pool_name} ({p.object_type})</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 10, color: '#888', display: 'block', marginBottom: 3 }}>
                    Time Window (seconds)
                  </label>
                  <input
                    type="number" value={timeWindowSeconds}
                    onChange={e => setTimeWindowSeconds(parseInt(e.target.value, 10) || 0)}
                    style={inputStyle}
                  />
                </div>
              </div>
              <button
                onClick={handlePredictDemand} disabled={loading}
                style={{
                  padding: '8px 18px', backgroundColor: '#0f3460', color: '#fdcb6e',
                  border: '1px solid #1a5276', borderRadius: 4,
                  cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600,
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? 'Predicting...' : '\uD83D\uDD2E Predict Demand'}
              </button>

              {predictResult && (
                <div style={{
                  marginTop: 10, padding: 12, backgroundColor: '#1a1a2e',
                  borderRadius: 6, border: '1px solid #0f3460', fontSize: 11,
                }}>
                  <div style={{ fontWeight: 600, color: '#fdcb6e', marginBottom: 8 }}>
                    Predicted Demand
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                      padding: '8px 16px', backgroundColor: '#16213e',
                      borderRadius: 6, textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Demand</div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: '#fdcb6e' }}>
                        {predictResult.predicted_demand}
                      </div>
                    </div>
                    <div style={{
                      padding: '8px 16px', backgroundColor: '#16213e',
                      borderRadius: 6, textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Confidence</div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: '#6bcb77' }}>
                        {(predictResult.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                  <div style={{ marginTop: 6, fontSize: 10, color: '#666' }}>
                    Time Window: {predictResult.time_window_seconds}s
                  </div>
                </div>
              )}
            </div>

            {/* Auto Optimize */}
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                Auto Optimize All Pools
              </div>
              <p style={{ fontSize: 11, color: '#888', margin: '0 0 10px 0' }}>
                Automatically analyze and optimize all object pools for peak performance.
              </p>
              <button
                onClick={handleAutoOptimize} disabled={loading}
                style={{
                  padding: '8px 18px', backgroundColor: '#0f3460', color: '#6bcb77',
                  border: '1px solid #1a5276', borderRadius: 4,
                  cursor: loading ? 'not-allowed' : 'pointer', fontSize: 12, fontWeight: 600,
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? 'Optimizing...' : '\u26A1 Auto Optimize'}
              </button>

              {optimizationResult && (
                <div style={{
                  marginTop: 10, padding: 12, backgroundColor: '#1a1a2e',
                  borderRadius: 6, border: '1px solid #0f3460',
                }}>
                  <div style={{ fontWeight: 600, color: '#6bcb77', marginBottom: 8 }}>
                    Optimization Results
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div style={{
                      padding: '8px', backgroundColor: '#16213e', borderRadius: 4, textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Pools Adjusted</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>
                        {optimizationResult.pools_adjusted}
                      </div>
                    </div>
                    <div style={{
                      padding: '8px', backgroundColor: '#16213e', borderRadius: 4, textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Objects Created</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>
                        {optimizationResult.objects_created}
                      </div>
                    </div>
                    <div style={{
                      padding: '8px', backgroundColor: '#16213e', borderRadius: 4, textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Objects Destroyed</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: '#ff6b6b' }}>
                        {optimizationResult.objects_destroyed}
                      </div>
                    </div>
                    <div style={{
                      padding: '8px', backgroundColor: '#16213e', borderRadius: 4, textAlign: 'center',
                    }}>
                      <div style={{ fontSize: 10, color: '#888' }}>Memory Savings</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>
                        {formatBytes(optimizationResult.memory_savings)}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ==================== STATUS TAB ==================== */}
        {activeTab === 'status' && status && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ padding: 14, backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460' }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                Object Pool System Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Pools</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#74b9ff' }}>
                    {status.total_pools}
                  </span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Objects</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#e0e0e0' }}>
                    {status.total_objects}
                  </span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>In Use</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>
                    {status.total_in_use}
                  </span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Available</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>
                    {status.total_available}
                  </span>
                </div>
              </div>
              <div style={{
                padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14,
              }}>
                <span style={{ fontSize: 11, color: '#888' }}>Memory Estimate</span>
                <span style={{ fontSize: 14, fontWeight: 700, color: '#a29bfe' }}>
                  {formatBytes(status.total_memory_estimate_bytes)}
                </span>
              </div>
            </div>

            {/* Per-pool stats */}
            <div style={{ fontWeight: 600, fontSize: 13, color: '#aaa' }}>
              Per-Pool Statistics ({status.pools?.length || 0})
            </div>
            {status.pools && status.pools.map(pool => (
              <div
                key={pool.id}
                style={{
                  padding: 10, backgroundColor: '#16213e', borderRadius: 8,
                  border: '1px solid #0f3460',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 12 }}>{pool.pool_name}</span>
                    <span style={{
                      marginLeft: 6, fontSize: 9, color: '#74b9ff',
                      backgroundColor: '#1a1a2e', padding: '1px 5px', borderRadius: 3,
                    }}>
                      {pool.object_type}
                    </span>
                  </div>
                  <span style={{ fontSize: 9, color: '#888' }}>{pool.id.slice(0, 8)}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 6 }}>
                  <div style={{ padding: '3px 5px', backgroundColor: '#1a1a2e', borderRadius: 3, textAlign: 'center', fontSize: 9 }}>
                    <div style={{ color: '#888' }}>Total</div>
                    <div style={{ color: '#e0e0e0', fontWeight: 600 }}>{pool.total}</div>
                  </div>
                  <div style={{ padding: '3px 5px', backgroundColor: '#1a1a2e', borderRadius: 3, textAlign: 'center', fontSize: 9 }}>
                    <div style={{ color: '#888' }}>Available</div>
                    <div style={{ color: '#6bcb77', fontWeight: 600 }}>{pool.available}</div>
                  </div>
                  <div style={{ padding: '3px 5px', backgroundColor: '#1a1a2e', borderRadius: 3, textAlign: 'center', fontSize: 9 }}>
                    <div style={{ color: '#888' }}>In Use</div>
                    <div style={{ color: '#fdcb6e', fontWeight: 600 }}>{pool.in_use}</div>
                  </div>
                  <div style={{ padding: '3px 5px', backgroundColor: '#1a1a2e', borderRadius: 3, textAlign: 'center', fontSize: 9 }}>
                    <div style={{ color: '#888' }}>Peak</div>
                    <div style={{ color: '#ff6b6b', fontWeight: 600 }}>{pool.peak_usage}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'status' && !status && (
          <div style={{
            textAlign: 'center', padding: 40, color: '#555',
            backgroundColor: '#16213e', borderRadius: 8, border: '1px solid #0f3460',
          }}>
            <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>
              {'\u2699\uFE0F'}
            </span>
            Loading system status...
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDDC2\uFE0F'} Object Pool Engine</span>
        <span>
          {status
            ? `${status.total_pools} pools · ${status.total_objects} objects · ${formatBytes(status.total_memory_estimate_bytes)}`
            : 'Disconnected'}
        </span>
      </div>
    </div>
  );
};

export default EngineObjectPoolPanel;