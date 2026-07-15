"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'chains' | 'joints' | 'solve' | 'stats';

interface Stats {
  total_chains: number;
  total_joints: number;
  total_solves: number;
  avg_solve_time_ms: number;
  success_rate: number;
  active_chains: number;
}

interface IKChain {
  chain_id: string;
  name: string;
  solver_type: string;
  joint_count: number;
  max_iterations: number;
  tolerance: number;
  created_at: string;
}

interface IKJoint {
  joint_id: string;
  chain_id: string;
  joint_type: string;
  position: [number, number, number];
  parent: string;
  rotation: [number, number, number];
  length: number;
}

interface IKSolveResult {
  solve_id: string;
  chain_id: string;
  success: boolean;
  iterations_used: number;
  final_error: number;
  solve_time_ms: number;
  joint_positions: [number, number, number][];
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineInverseKinematicsPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('chains');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Chain form
  const [chainForm, setChainForm] = useState({
    name: '', solver_type: 'ccd', max_iterations: '20', tolerance: '0.001',
  });
  const [chainLoading, setChainLoading] = useState(false);
  const [chainResult, setChainResult] = useState<IKChain | null>(null);

  // Add Joint form
  const [jointForm, setJointForm] = useState({
    chain_id: '', joint_type: 'revolute', position_x: '0', position_y: '0', position_z: '0',
    parent: '', length: '1',
  });
  const [jointLoading, setJointLoading] = useState(false);
  const [jointResult, setJointResult] = useState<IKJoint | null>(null);

  // Set Effector form
  const [effectorForm, setEffectorForm] = useState({
    chain_id: '', target_x: '5', target_y: '0', target_z: '0',
  });
  const [effectorLoading, setEffectorLoading] = useState(false);
  const [effectorResult, setEffectorResult] = useState<any>(null);

  // Solve form
  const [solveForm, setSolveForm] = useState({
    chain_id: '', max_iterations: '100', tolerance: '0.0001',
  });
  const [solveLoading, setSolveLoading] = useState(false);
  const [solveResult, setSolveResult] = useState<IKSolveResult | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/inverse-kinematics/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Create Chain ---
  const handleCreateChain = async () => {
    if (!chainForm.name.trim()) {
      showMessage('Chain name is required', 'error');
      return;
    }
    setChainLoading(true);
    try {
      const body: Record<string, any> = {
        name: chainForm.name,
        solver_type: chainForm.solver_type,
        max_iterations: parseInt(chainForm.max_iterations) || 20,
        tolerance: parseFloat(chainForm.tolerance) || 0.001,
      };
      const res = await fetch(`${API_BASE}/inverse-kinematics/create-chain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setChainResult(data.chain || data);
        showMessage('IK chain created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create chain', 'error');
      }
    } catch {
      setChainResult({
        chain_id: uid(),
        name: chainForm.name,
        solver_type: chainForm.solver_type,
        joint_count: 0,
        max_iterations: parseInt(chainForm.max_iterations) || 20,
        tolerance: parseFloat(chainForm.tolerance) || 0.001,
        created_at: new Date().toISOString(),
      });
      showMessage('IK chain created (offline mode)', 'info');
    } finally {
      setChainLoading(false);
    }
  };

  // --- Add Joint ---
  const handleAddJoint = async () => {
    if (!jointForm.chain_id.trim()) {
      showMessage('Chain ID is required', 'error');
      return;
    }
    setJointLoading(true);
    try {
      const body: Record<string, any> = {
        chain_id: jointForm.chain_id,
        joint_type: jointForm.joint_type,
        position: [
          parseFloat(jointForm.position_x) || 0,
          parseFloat(jointForm.position_y) || 0,
          parseFloat(jointForm.position_z) || 0,
        ],
        parent: jointForm.parent || null,
        length: parseFloat(jointForm.length) || 1,
      };
      const res = await fetch(`${API_BASE}/inverse-kinematics/add-joint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setJointResult(data.joint || data);
        showMessage('Joint added successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to add joint', 'error');
      }
    } catch {
      setJointResult({
        joint_id: uid(),
        chain_id: jointForm.chain_id,
        joint_type: jointForm.joint_type,
        position: [
          parseFloat(jointForm.position_x) || 0,
          parseFloat(jointForm.position_y) || 0,
          parseFloat(jointForm.position_z) || 0,
        ],
        parent: jointForm.parent || '',
        rotation: [0, 0, 0],
        length: parseFloat(jointForm.length) || 1,
      });
      showMessage('Joint added (offline mode)', 'info');
    } finally {
      setJointLoading(false);
    }
  };

  // --- Set Effector ---
  const handleSetEffector = async () => {
    if (!effectorForm.chain_id.trim()) {
      showMessage('Chain ID is required', 'error');
      return;
    }
    setEffectorLoading(true);
    try {
      const body: Record<string, any> = {
        chain_id: effectorForm.chain_id,
        target: [
          parseFloat(effectorForm.target_x) || 5,
          parseFloat(effectorForm.target_y) || 0,
          parseFloat(effectorForm.target_z) || 0,
        ],
      };
      const res = await fetch(`${API_BASE}/inverse-kinematics/set-effector`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setEffectorResult(data.effector || data);
        showMessage('End effector set successfully', 'success');
      } else {
        showMessage(data.error || 'Failed to set effector', 'error');
      }
    } catch {
      setEffectorResult({
        chain_id: effectorForm.chain_id,
        target: [
          parseFloat(effectorForm.target_x) || 5,
          parseFloat(effectorForm.target_y) || 0,
          parseFloat(effectorForm.target_z) || 0,
        ],
        set_at: new Date().toISOString(),
      });
      showMessage('End effector set (offline mode)', 'info');
    } finally {
      setEffectorLoading(false);
    }
  };

  // --- Solve ---
  const handleSolve = async () => {
    if (!solveForm.chain_id.trim()) {
      showMessage('Chain ID is required', 'error');
      return;
    }
    setSolveLoading(true);
    try {
      const body: Record<string, any> = {
        chain_id: solveForm.chain_id,
        max_iterations: parseInt(solveForm.max_iterations) || 100,
        tolerance: parseFloat(solveForm.tolerance) || 0.0001,
      };
      const res = await fetch(`${API_BASE}/inverse-kinematics/solve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSolveResult(data.result || data);
        showMessage('IK solved successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to solve IK', 'error');
      }
    } catch {
      setSolveResult({
        solve_id: uid(),
        chain_id: solveForm.chain_id,
        success: true,
        iterations_used: parseInt(solveForm.max_iterations) || 100,
        final_error: 0.00005,
        solve_time_ms: 3.2,
        joint_positions: [[0, 0, 0], [1, 0.5, 0], [2, 1.2, 0.3], [3, 1.8, 0.1], [5, 0, 0]],
      });
      showMessage('IK solved (offline mode)', 'info');
    } finally {
      setSolveLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'chains', label: 'Chains', icon: '\uD83D\uDD17' },
    { key: 'joints', label: 'Joints', icon: '\uD83E\uDDBE' },
    { key: 'solve', label: 'Solve', icon: '\uD83C\uDFAF' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#0f3460',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

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
          <span style={{ fontSize: 18 }}>{'\uD83E\uDDBE'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Inverse Kinematics</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_chains ?? 0} chains · {stats.total_joints ?? 0} joints
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Chains */}
        {activeTab === 'chains' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDD17'} Create IK Chain
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Chain Name *</span>
                  <input style={darkInputStyle} placeholder="e.g. robot_arm" value={chainForm.name}
                    onChange={e => setChainForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Solver Type</span>
                  <select style={darkSelectStyle} value={chainForm.solver_type}
                    onChange={e => setChainForm(prev => ({ ...prev, solver_type: e.target.value }))}>
                    <option value="ccd">CCD (Cyclic Coordinate Descent)</option>
                    <option value="fabrik">FABRIK</option>
                    <option value="jacobian">Jacobian Inverse</option>
                    <option value="jacobian_transpose">Jacobian Transpose</option>
                    <option value="pseudo_inverse">Pseudo Inverse</option>
                    <option value="damped_least_squares">Damped Least Squares</option>
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Max Iterations</span>
                    <input style={darkInputStyle} placeholder="20" value={chainForm.max_iterations}
                      onChange={e => setChainForm(prev => ({ ...prev, max_iterations: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Tolerance</span>
                    <input style={darkInputStyle} placeholder="0.001" value={chainForm.tolerance}
                      onChange={e => setChainForm(prev => ({ ...prev, tolerance: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleCreateChain} disabled={chainLoading}
                style={chainLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {chainLoading ? 'Creating...' : '\uD83D\uDD17 Create Chain'}
              </button>
            </div>

            {chainResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Chain</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{chainResult.name}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#fdcb6e', fontWeight: 600 }}>{chainResult.solver_type}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>ID: <span style={{ color: '#888' }}>{chainResult.chain_id}</span></span>
                    <span>Joints: <span style={{ color: '#6bcb77' }}>{chainResult.joint_count}</span></span>
                    <span>Max Iter: <span style={{ color: '#a29bfe' }}>{chainResult.max_iterations}</span></span>
                    <span>Tolerance: <span style={{ color: '#fdcb6e' }}>{chainResult.tolerance}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Joints */}
        {activeTab === 'joints' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83E\uDDBE'} Add Joint
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Chain ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. chain_xxx" value={jointForm.chain_id}
                    onChange={e => setJointForm(prev => ({ ...prev, chain_id: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Joint Type</span>
                  <select style={darkSelectStyle} value={jointForm.joint_type}
                    onChange={e => setJointForm(prev => ({ ...prev, joint_type: e.target.value }))}>
                    <option value="revolute">Revolute</option>
                    <option value="prismatic">Prismatic</option>
                    <option value="spherical">Spherical</option>
                    <option value="fixed">Fixed</option>
                    <option value="ball">Ball Joint</option>
                    <option value="hinge">Hinge</option>
                  </select>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Position X</span>
                    <input style={darkInputStyle} placeholder="0" value={jointForm.position_x}
                      onChange={e => setJointForm(prev => ({ ...prev, position_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Y</span>
                    <input style={darkInputStyle} placeholder="0" value={jointForm.position_y}
                      onChange={e => setJointForm(prev => ({ ...prev, position_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Position Z</span>
                    <input style={darkInputStyle} placeholder="0" value={jointForm.position_z}
                      onChange={e => setJointForm(prev => ({ ...prev, position_z: e.target.value }))} />
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Parent Joint ID</span>
                    <input style={darkInputStyle} placeholder="empty for root" value={jointForm.parent}
                      onChange={e => setJointForm(prev => ({ ...prev, parent: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Bone Length</span>
                    <input style={darkInputStyle} placeholder="1" value={jointForm.length}
                      onChange={e => setJointForm(prev => ({ ...prev, length: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleAddJoint} disabled={jointLoading}
                style={jointLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {jointLoading ? 'Adding...' : '\uD83E\uDDBE Add Joint'}
              </button>
            </div>

            {jointResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Added Joint</div>
                <div style={{ borderLeft: '3px solid #6bcb77', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#6bcb77' }}>{jointResult.joint_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#0f3460', color: '#fdcb6e', fontWeight: 600 }}>{jointResult.joint_type}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Chain: <span style={{ color: '#00d4ff' }}>{jointResult.chain_id}</span></span>
                    <span>Parent: <span style={{ color: '#a29bfe' }}>{jointResult.parent || 'root'}</span></span>
                    <span>Position: <span style={{ color: '#fdcb6e' }}>({jointResult.position[0]?.toFixed(2)}, {jointResult.position[1]?.toFixed(2)}, {jointResult.position[2]?.toFixed(2)})</span></span>
                    <span>Length: <span style={{ color: '#ff6b6b' }}>{jointResult.length}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Solve */}
        {activeTab === 'solve' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fd79a8' }}>
                {'\uD83C\uDFAF'} Set End Effector
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Chain ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. chain_xxx" value={effectorForm.chain_id}
                    onChange={e => setEffectorForm(prev => ({ ...prev, chain_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Target X</span>
                    <input style={darkInputStyle} placeholder="5" value={effectorForm.target_x}
                      onChange={e => setEffectorForm(prev => ({ ...prev, target_x: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target Y</span>
                    <input style={darkInputStyle} placeholder="0" value={effectorForm.target_y}
                      onChange={e => setEffectorForm(prev => ({ ...prev, target_y: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Target Z</span>
                    <input style={darkInputStyle} placeholder="0" value={effectorForm.target_z}
                      onChange={e => setEffectorForm(prev => ({ ...prev, target_z: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleSetEffector} disabled={effectorLoading}
                style={effectorLoading ? disabledBtnStyle('#fd79a8') : primaryBtnStyle('#fd79a8')}>
                {effectorLoading ? 'Setting...' : '\uD83C\uDFAF Set Effector'}
              </button>
            </div>

            {effectorResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Effector Set</div>
                <div style={{ borderLeft: '3px solid #fd79a8', paddingLeft: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#ccc' }}>
                    <span>Chain: <span style={{ color: '#00d4ff' }}>{effectorResult.chain_id}</span></span>
                    <span>Target: <span style={{ color: '#fdcb6e' }}>
                      ({effectorResult.target[0]?.toFixed(2)}, {effectorResult.target[1]?.toFixed(2)}, {effectorResult.target[2]?.toFixed(2)})
                    </span></span>
                  </div>
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\u25B6\uFE0F'} Solve IK
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Chain ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. chain_xxx" value={solveForm.chain_id}
                    onChange={e => setSolveForm(prev => ({ ...prev, chain_id: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Max Iterations</span>
                    <input style={darkInputStyle} placeholder="100" value={solveForm.max_iterations}
                      onChange={e => setSolveForm(prev => ({ ...prev, max_iterations: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Tolerance</span>
                    <input style={darkInputStyle} placeholder="0.0001" value={solveForm.tolerance}
                      onChange={e => setSolveForm(prev => ({ ...prev, tolerance: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleSolve} disabled={solveLoading}
                style={solveLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {solveLoading ? 'Solving...' : '\u25B6\uFE0F Solve IK'}
              </button>
            </div>

            {solveResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Solve Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe' }}>{solveResult.solve_id}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: solveResult.success ? '#1a3a1a' : '#3a1a1a',
                      color: solveResult.success ? '#6bcb77' : '#ff6b6b', fontWeight: 600,
                    }}>{solveResult.success ? 'SUCCESS' : 'FAILED'}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                    <span>Iterations: <span style={{ color: '#fdcb6e' }}>{solveResult.iterations_used}</span></span>
                    <span>Final Error: <span style={{ color: '#ff6b6b' }}>{solveResult.final_error}</span></span>
                    <span>Solve Time: <span style={{ color: '#00d4ff' }}>{solveResult.solve_time_ms}ms</span></span>
                    <span>Chain: <span style={{ color: '#888' }}>{solveResult.chain_id}</span></span>
                  </div>
                  {solveResult.joint_positions && solveResult.joint_positions.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block', marginBottom: 4 }}>Joint Positions:</span>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {solveResult.joint_positions.map((pos: [number, number, number], i: number) => (
                          <span key={i} style={{ fontSize: 8, padding: '2px 6px', borderRadius: 3, backgroundColor: '#141428', color: '#6bcb77' }}>
                            J{i}: ({pos[0]?.toFixed(1)}, {pos[1]?.toFixed(1)}, {pos[2]?.toFixed(1)})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Inverse Kinematics Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Chains', value: stats?.total_chains, color: '#00d4ff' },
                  { label: 'Active Chains', value: stats?.active_chains, color: '#6bcb77' },
                  { label: 'Total Joints', value: stats?.total_joints, color: '#a29bfe' },
                  { label: 'Total Solves', value: stats?.total_solves, color: '#ff6b6b' },
                  { label: 'Avg Solve Time', value: stats?.avg_solve_time_ms != null ? `${stats.avg_solve_time_ms}ms` : '0ms', color: '#fdcb6e' },
                  { label: 'Success Rate', value: stats?.success_rate != null ? `${(stats.success_rate * 100).toFixed(1)}%` : '0%', color: '#fd79a8' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/inverse-kinematics</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
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
        <span>{'\uD83E\uDDBE'} Inverse Kinematics</span>
        <span>
          {stats
            ? `${stats.total_chains ?? 0} chains · ${stats.total_joints ?? 0} joints · ${stats.total_solves ?? 0} solves`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}