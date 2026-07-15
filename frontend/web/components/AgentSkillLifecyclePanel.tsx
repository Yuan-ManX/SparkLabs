"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/agent';

type TabId = 'overview' | 'create-skill' | 'skills' | 'record-experience' | 'refine' | 'artifacts' | 'history';

interface Stats {
  total_skills: number;
  total_experiences: number;
  total_refinements: number;
  total_artifacts: number;
  total_lifecycle_events: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function AgentSkillLifecyclePanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Create Skill form
  const [skillForm, setSkillForm] = useState({ name: '', domain: '', description: '', initial_steps: '', initial_parameters: '' });
  const [skillLoading, setSkillLoading] = useState(false);
  const [skillResult, setSkillResult] = useState<any>(null);

  // Skills / Discover
  const [discoverDomain, setDiscoverDomain] = useState('');
  const [skills, setSkills] = useState<any[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);

  // Record Experience form
  const [experienceForm, setExperienceForm] = useState({ skill_id: '', success: 'true', execution_time: '', context: '', outcome_notes: '' });
  const [experienceLoading, setExperienceLoading] = useState(false);
  const [experienceResult, setExperienceResult] = useState<any>(null);

  // Refine form
  const [refineForm, setRefineForm] = useState({ skill_id: '', strategy: 'incremental', focus_area: '' });
  const [refineLoading, setRefineLoading] = useState(false);
  const [refineResult, setRefineResult] = useState<any>(null);

  // Artifacts form
  const [artifactsForm, setArtifactsForm] = useState({ skill_id: '' });
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [artifactsLoading, setArtifactsLoading] = useState(false);

  // History form
  const [historyForm, setHistoryForm] = useState({ skill_id: '' });
  const [history, setHistory] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/skill-lifecycle/stats`);
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

  // --- Create Skill ---
  const handleCreateSkill = async () => {
    if (!skillForm.name.trim() || !skillForm.domain.trim()) {
      showMessage('Name and Domain are required', 'error');
      return;
    }
    setSkillLoading(true);
    try {
      const body: Record<string, any> = {
        name: skillForm.name,
        domain: skillForm.domain,
        description: skillForm.description,
        initial_steps: skillForm.initial_steps ? skillForm.initial_steps.split(',').map(s => s.trim()).filter(Boolean) : [],
        initial_parameters: skillForm.initial_parameters ? JSON.parse(skillForm.initial_parameters) : {},
      };
      const res = await fetch(`${API_BASE}/skill-lifecycle/create-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setSkillResult(data.skill || data);
        showMessage('Skill created successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to create skill', 'error');
      }
    } catch {
      setSkillResult({
        skill_id: uid(),
        name: skillForm.name,
        domain: skillForm.domain,
        description: skillForm.description,
        created_at: 'just now',
      });
      showMessage('Skill created (offline mode)', 'info');
    } finally {
      setSkillLoading(false);
    }
  };

  // --- Discover Skills ---
  const handleDiscoverSkills = async () => {
    if (!discoverDomain.trim()) {
      showMessage('Domain is required', 'error');
      return;
    }
    setSkillsLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('domain', discoverDomain);
      const res = await fetch(`${API_BASE}/skill-lifecycle/discover?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setSkills(data.skills || data || []);
        showMessage('Skills discovered', 'success');
      } else {
        showMessage(data.error || 'Failed to discover skills', 'error');
      }
    } catch {
      setSkills([
        { skill_id: uid(), name: 'Resource Gathering', domain: discoverDomain, version: '1.2', confidence: 0.85, usage_count: 42 },
        { skill_id: uid(), name: 'Combat Tactics', domain: discoverDomain, version: '2.0', confidence: 0.92, usage_count: 18 },
        { skill_id: uid(), name: 'Social Diplomacy', domain: discoverDomain, version: '1.0', confidence: 0.73, usage_count: 7 },
      ]);
      showMessage('Skills discovered (offline mode)', 'info');
    } finally {
      setSkillsLoading(false);
    }
  };

  // --- Record Experience ---
  const handleRecordExperience = async () => {
    if (!experienceForm.skill_id.trim()) {
      showMessage('Skill ID is required', 'error');
      return;
    }
    setExperienceLoading(true);
    try {
      const body: Record<string, any> = {
        skill_id: experienceForm.skill_id,
        success: experienceForm.success === 'true',
        execution_time: experienceForm.execution_time ? parseFloat(experienceForm.execution_time) : null,
        context: experienceForm.context,
        outcome_notes: experienceForm.outcome_notes,
      };
      const res = await fetch(`${API_BASE}/skill-lifecycle/record-experience`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setExperienceResult(data.experience || data);
        showMessage('Experience recorded successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to record experience', 'error');
      }
    } catch {
      setExperienceResult({
        experience_id: uid(),
        skill_id: experienceForm.skill_id,
        success: experienceForm.success === 'true',
        outcome_notes: experienceForm.outcome_notes,
        recorded_at: 'just now',
      });
      showMessage('Experience recorded (offline mode)', 'info');
    } finally {
      setExperienceLoading(false);
    }
  };

  // --- Refine Skill ---
  const handleRefineSkill = async () => {
    if (!refineForm.skill_id.trim()) {
      showMessage('Skill ID is required', 'error');
      return;
    }
    setRefineLoading(true);
    try {
      const body: Record<string, any> = {
        skill_id: refineForm.skill_id,
        strategy: refineForm.strategy,
        focus_area: refineForm.focus_area,
      };
      const res = await fetch(`${API_BASE}/skill-lifecycle/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setRefineResult(data.refinement || data);
        showMessage('Skill refined successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to refine skill', 'error');
      }
    } catch {
      setRefineResult({
        refinement_id: uid(),
        skill_id: refineForm.skill_id,
        strategy: refineForm.strategy,
        focus_area: refineForm.focus_area,
        new_version: '1.3',
        refined_at: 'just now',
      });
      showMessage('Skill refined (offline mode)', 'info');
    } finally {
      setRefineLoading(false);
    }
  };

  // --- Fetch Artifacts ---
  const handleFetchArtifacts = async () => {
    if (!artifactsForm.skill_id.trim()) {
      showMessage('Skill ID is required', 'error');
      return;
    }
    setArtifactsLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('skill_id', artifactsForm.skill_id);
      const res = await fetch(`${API_BASE}/skill-lifecycle/artifacts?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setArtifacts(data.artifacts || data || []);
        showMessage('Artifacts loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load artifacts', 'error');
      }
    } catch {
      setArtifacts([
        { artifact_id: uid(), type: 'model', name: 'Skill Model v1.2', size: '2.4MB', created_at: '3d ago' },
        { artifact_id: uid(), type: 'dataset', name: 'Training Data Batch 7', size: '15.8MB', created_at: '1d ago' },
        { artifact_id: uid(), type: 'config', name: 'Hyperparameters v2', size: '8KB', created_at: '12h ago' },
      ]);
      showMessage('Artifacts loaded (offline mode)', 'info');
    } finally {
      setArtifactsLoading(false);
    }
  };

  // --- Fetch History ---
  const handleFetchHistory = async () => {
    if (!historyForm.skill_id.trim()) {
      showMessage('Skill ID is required', 'error');
      return;
    }
    setHistoryLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('skill_id', historyForm.skill_id);
      const res = await fetch(`${API_BASE}/skill-lifecycle/history?${params.toString()}`);
      const data = await res.json();
      if (res.ok) {
        setHistory(data.history || data || []);
        showMessage('History loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load history', 'error');
      }
    } catch {
      setHistory([
        { event_id: uid(), event_type: 'created', description: 'Skill initialized', timestamp: '7d ago' },
        { event_id: uid(), event_type: 'refined', description: 'Parameter tuning applied', timestamp: '5d ago' },
        { event_id: uid(), event_type: 'experience', description: 'Successful use in scenario X', timestamp: '2d ago' },
        { event_id: uid(), event_type: 'refined', description: 'Strategy adjustment for edge cases', timestamp: '1d ago' },
      ]);
      showMessage('History loaded (offline mode)', 'info');
    } finally {
      setHistoryLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83D\uDCCB' },
    { key: 'create-skill', label: 'Create Skill', icon: '\u2795' },
    { key: 'skills', label: 'Discover Skills', icon: '\uD83D\uDD0D' },
    { key: 'record-experience', label: 'Record Experience', icon: '\uD83D\uDCDD' },
    { key: 'refine', label: 'Refine', icon: '\uD83D\uDD27' },
    { key: 'artifacts', label: 'Artifacts', icon: '\uD83D\uDCE6' },
    { key: 'history', label: 'History', icon: '\uD83D\uDCC5' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#141428', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#22223a', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#2d3a4a',
    color,
    border: '1px solid #3d4a5a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a2a3a',
    color: '#666',
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCCB'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Skill Lifecycle</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_skills ?? 0} skills · {stats.total_refinements ?? 0} refinements
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
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff',
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
              backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
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

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCB'} Skill Lifecycle Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Skills', value: stats?.total_skills, color: '#74b9ff' },
                  { label: 'Total Experiences', value: stats?.total_experiences, color: '#fdcb6e' },
                  { label: 'Total Refinements', value: stats?.total_refinements, color: '#6bcb77' },
                  { label: 'Total Artifacts', value: stats?.total_artifacts, color: '#a29bfe' },
                  { label: 'Lifecycle Events', value: stats?.total_lifecycle_events, color: '#e17055' },
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
          </div>
        )}

        {/* Tab: Create Skill */}
        {activeTab === 'create-skill' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#74b9ff' }}>
                {'\u2795'} Create Skill
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Name *</span>
                    <input style={darkInputStyle} placeholder="e.g. Resource Gathering" value={skillForm.name} onChange={e => setSkillForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Domain *</span>
                    <input style={darkInputStyle} placeholder="e.g. survival, combat" value={skillForm.domain} onChange={e => setSkillForm(prev => ({ ...prev, domain: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Description</span>
                  <textarea style={darkTextareaStyle} placeholder="Describe the skill..." rows={2} value={skillForm.description} onChange={e => setSkillForm(prev => ({ ...prev, description: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Initial Steps (comma-sep)</span>
                  <input style={darkInputStyle} placeholder="step1, step2, step3" value={skillForm.initial_steps} onChange={e => setSkillForm(prev => ({ ...prev, initial_steps: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Initial Parameters (JSON)</span>
                  <textarea style={{ ...darkTextareaStyle, fontFamily: 'monospace' }} placeholder='{"efficiency": 0.8, "range": 10}' rows={2} value={skillForm.initial_parameters} onChange={e => setSkillForm(prev => ({ ...prev, initial_parameters: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleCreateSkill} disabled={skillLoading} style={skillLoading ? disabledBtnStyle('#74b9ff') : primaryBtnStyle('#74b9ff')}>
                {skillLoading ? 'Creating...' : '\u2795 Create Skill'}
              </button>
            </div>
            {skillResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Created Skill</div>
                <div style={{ borderLeft: '3px solid #74b9ff', paddingLeft: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{skillResult.name}</div>
                  {skillResult.description && <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{skillResult.description}</div>}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Domain: <span style={{ color: '#fdcb6e' }}>{skillResult.domain}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{skillResult.skill_id}</span></span>
                    <span>Created: <span style={{ color: '#6bcb77' }}>{skillResult.created_at}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Discover Skills */}
        {activeTab === 'skills' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83D\uDD0D'} Discover Skills
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Domain *</span>
                  <input style={darkInputStyle} placeholder="e.g. survival, combat, social" value={discoverDomain} onChange={e => setDiscoverDomain(e.target.value)} />
                </div>
              </div>
              <button
                onClick={handleDiscoverSkills}
                disabled={skillsLoading}
                style={{
                  ...(skillsLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')),
                  width: '100%', marginBottom: 10,
                }}
              >
                {skillsLoading ? 'Discovering...' : '\uD83D\uDD0D Discover Skills'}
              </button>
              {skills.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {skills.map(sk => (
                    <div key={sk.skill_id} style={{
                      padding: 12, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: '3px solid #6bcb77',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{sk.name}</span>
                        <span style={{ fontSize: 9, color: '#666' }}>v{sk.version}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 10, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Domain: <span style={{ color: '#74b9ff' }}>{sk.domain}</span></span>
                        <span>Confidence: <span style={{ color: '#fdcb6e' }}>{sk.confidence}</span></span>
                        <span>Used: <span style={{ color: '#a29bfe' }}>{sk.usage_count}x</span></span>
                        <span>ID: <span style={{ color: '#888' }}>{sk.skill_id}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Record Experience */}
        {activeTab === 'record-experience' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDCDD'} Record Experience
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Skill ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. skill_xxx" value={experienceForm.skill_id} onChange={e => setExperienceForm(prev => ({ ...prev, skill_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Success</span>
                    <select style={darkSelectStyle} value={experienceForm.success} onChange={e => setExperienceForm(prev => ({ ...prev, success: e.target.value }))}>
                      <option value="true">Success</option>
                      <option value="false">Failure</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Execution Time (ms)</span>
                  <input style={darkInputStyle} placeholder="e.g. 150.5" value={experienceForm.execution_time} onChange={e => setExperienceForm(prev => ({ ...prev, execution_time: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Context</span>
                  <textarea style={darkTextareaStyle} placeholder="Context in which the skill was used..." rows={2} value={experienceForm.context} onChange={e => setExperienceForm(prev => ({ ...prev, context: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Outcome Notes</span>
                  <textarea style={darkTextareaStyle} placeholder="Notes on the outcome..." rows={2} value={experienceForm.outcome_notes} onChange={e => setExperienceForm(prev => ({ ...prev, outcome_notes: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRecordExperience} disabled={experienceLoading} style={experienceLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}>
                {experienceLoading ? 'Recording...' : '\uD83D\uDCDD Record Experience'}
              </button>
            </div>
            {experienceResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Experience Recorded</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>
                      {experienceResult.success ? '\u2705 Success' : '\u274C Failure'}
                    </span>
                  </div>
                  {experienceResult.outcome_notes && <div style={{ fontSize: 11, color: '#ccc', marginBottom: 4 }}>{experienceResult.outcome_notes}</div>}
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Skill: <span style={{ color: '#74b9ff' }}>{experienceResult.skill_id}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{experienceResult.experience_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Refine */}
        {activeTab === 'refine' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD27'} Refine Skill
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Skill ID *</span>
                    <input style={darkInputStyle} placeholder="e.g. skill_xxx" value={refineForm.skill_id} onChange={e => setRefineForm(prev => ({ ...prev, skill_id: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Strategy</span>
                    <select style={darkSelectStyle} value={refineForm.strategy} onChange={e => setRefineForm(prev => ({ ...prev, strategy: e.target.value }))}>
                      <option value="incremental">Incremental</option>
                      <option value="reinforcement">Reinforcement Learning</option>
                      <option value="evolutionary">Evolutionary</option>
                      <option value="transfer">Transfer Learning</option>
                    </select>
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Focus Area</span>
                  <input style={darkInputStyle} placeholder="e.g. efficiency, accuracy, speed" value={refineForm.focus_area} onChange={e => setRefineForm(prev => ({ ...prev, focus_area: e.target.value }))} />
                </div>
              </div>
              <button onClick={handleRefineSkill} disabled={refineLoading} style={refineLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}>
                {refineLoading ? 'Refining...' : '\uD83D\uDD27 Refine Skill'}
              </button>
            </div>
            {refineResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Refinement Result</div>
                <div style={{ borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>New Version: <span style={{ color: '#a29bfe' }}>{refineResult.new_version}</span></span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Skill: <span style={{ color: '#74b9ff' }}>{refineResult.skill_id}</span></span>
                    <span>Strategy: <span style={{ color: '#fdcb6e' }}>{refineResult.strategy}</span></span>
                    <span>Focus: <span style={{ color: '#6bcb77' }}>{refineResult.focus_area}</span></span>
                    <span>ID: <span style={{ color: '#888' }}>{refineResult.refinement_id}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Artifacts */}
        {activeTab === 'artifacts' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCE6'} Skill Artifacts
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Skill ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. skill_xxx" value={artifactsForm.skill_id} onChange={e => setArtifactsForm(prev => ({ ...prev, skill_id: e.target.value }))} />
                </div>
              </div>
              <button
                onClick={handleFetchArtifacts}
                disabled={artifactsLoading}
                style={{
                  ...(artifactsLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')),
                  width: '100%', marginBottom: 10,
                }}
              >
                {artifactsLoading ? 'Loading...' : '\uD83D\uDCE6 Fetch Artifacts'}
              </button>
              {artifacts.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {artifacts.map(a => (
                    <div key={a.artifact_id} style={{
                      padding: 12, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: '3px solid #00d4ff',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{a.name}</span>
                        <span style={{ fontSize: 9, color: '#666' }}>{a.created_at}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 10, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Type: <span style={{ color: '#fdcb6e' }}>{a.type}</span></span>
                        <span>Size: <span style={{ color: '#a29bfe' }}>{a.size}</span></span>
                        <span>ID: <span style={{ color: '#888' }}>{a.artifact_id}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: History */}
        {activeTab === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#e17055' }}>
                {'\uD83D\uDCC5'} Skill History
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Skill ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. skill_xxx" value={historyForm.skill_id} onChange={e => setHistoryForm(prev => ({ ...prev, skill_id: e.target.value }))} />
                </div>
              </div>
              <button
                onClick={handleFetchHistory}
                disabled={historyLoading}
                style={{
                  ...(historyLoading ? disabledBtnStyle('#e17055') : primaryBtnStyle('#e17055')),
                  width: '100%', marginBottom: 10,
                }}
              >
                {historyLoading ? 'Loading...' : '\uD83D\uDCC5 Fetch History'}
              </button>
              {history.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {history.map(h => (
                    <div key={h.event_id} style={{
                      padding: 12, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e',
                      borderLeft: '3px solid #e17055',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{h.event_type}</span>
                        <span style={{ fontSize: 9, color: '#666' }}>{h.timestamp}</span>
                      </div>
                      {h.description && <div style={{ fontSize: 10, color: '#888' }}>{h.description}</div>}
                      <div style={{ fontSize: 9, color: '#666', marginTop: 2 }}>
                        <span>ID: <span style={{ color: '#888' }}>{h.event_id}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
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
        <span>{'\uD83D\uDCCB'} Skill Lifecycle</span>
        <span>
          {stats
            ? `${stats.total_skills ?? 0} skills · ${stats.total_experiences ?? 0} experiences · ${stats.total_refinements ?? 0} refinements`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}