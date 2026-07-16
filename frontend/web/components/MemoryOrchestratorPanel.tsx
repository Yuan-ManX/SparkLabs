import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'memories' | 'skills' | 'experiences' | 'nudges';

interface MemoryEntry {
  memory_id: string;
  category: string;
  priority: string;
  content: string;
  context: Record<string, unknown>;
  tags: string[];
  embedding_hash: string;
  access_count: number;
  last_accessed: number;
  created_at: number;
  expires_at: number;
  linked_memories: string[];
  confidence_score: number;
}

interface SkillDefinition {
  skill_id: string;
  name: string;
  description: string;
  version: number;
  status: string;
  trigger_patterns: string[];
  action_sequence: Record<string, unknown>[];
  preconditions: string[];
  postconditions: string[];
  success_rate: number;
  usage_count: number;
  improvement_history: Record<string, unknown>[];
  created_at: number;
  updated_at: number;
  parent_skill_id: string;
  derived_skills: string[];
}

interface ExperienceRecord {
  experience_id: string;
  session_id: string;
  summary: string;
  extracted_patterns: Record<string, unknown>[];
  lessons_learned: string[];
  skill_improvements: string[];
  memory_links: string[];
  timestamp: number;
  consolidation_score: number;
}

interface NudgeSchedule {
  nudge_id: string;
  trigger_type: string;
  interval_seconds: number;
  target_memory_ids: string[];
  target_skill_ids: string[];
  last_triggered: number;
  next_trigger: number;
  enabled: boolean;
  max_triggers: number;
  trigger_count: number;
}

interface MemoryStats {
  memory: {
    total_memories: number;
    by_category: Record<string, number>;
    by_priority: Record<string, number>;
    total_stored: number;
  };
  skills: {
    total_skills: number;
    by_status: Record<string, number>;
    total_created: number;
  };
  total_experiences: number;
  total_experiences_recorded: number;
  total_nudges: number;
  total_nudges_triggered: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const MEMORY_CATEGORIES = ['short_term', 'long_term', 'episodic', 'semantic', 'procedural'];
const MEMORY_PRIORITIES = ['critical', 'high', 'medium', 'low', 'transient'];
const SKILL_STATUSES = ['draft', 'active', 'improving', 'deprecated', 'archived'];
const NUDGE_TRIGGERS = ['time_based', 'context_based', 'event_based', 'manual'];

const MemoryOrchestratorPanel: React.FC = () => {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [skills, setSkills] = useState<SkillDefinition[]>([]);
  const [experiences, setExperiences] = useState<ExperienceRecord[]>([]);
  const [nudges, setNudges] = useState<NudgeSchedule[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('memories');

  const [memoryContent, setMemoryContent] = useState('');
  const [memoryCategory, setMemoryCategory] = useState('short_term');
  const [memoryPriority, setMemoryPriority] = useState('medium');
  const [memoryTags, setMemoryTags] = useState('');
  const [memoryTTL, setMemoryTTL] = useState('86400');

  const [retrieveTags, setRetrieveTags] = useState('');
  const [retrieveCategory, setRetrieveCategory] = useState('');
  const [retrievePriority, setRetrievePriority] = useState('');
  const [retrieveMinConfidence, setRetrieveMinConfidence] = useState('0.5');
  const [retrieveLimit, setRetrieveLimit] = useState('50');
  const [retrievedMemories, setRetrievedMemories] = useState<MemoryEntry[]>([]);

  const [skillName, setSkillName] = useState('');
  const [skillDescription, setSkillDescription] = useState('');
  const [skillTriggers, setSkillTriggers] = useState('');
  const [skillPreconditions, setSkillPreconditions] = useState('');
  const [skillPostconditions, setSkillPostconditions] = useState('');

  const [improveSkillId, setImproveSkillId] = useState('');
  const [improveSuccess, setImproveSuccess] = useState(true);
  const [improveNotes, setImproveNotes] = useState('');

  const [expSessionId, setExpSessionId] = useState('');
  const [expSummary, setExpSummary] = useState('');
  const [expLessons, setExpLessons] = useState('');

  const apiBase = API_ROOT + '/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/memory-orchestrator/stats`);
      const data = await res.json();
      setStats(data);
    } catch {}
  }, []);

  const fetchMemories = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/memory-orchestrator/memories`);
      const data = await res.json();
      setMemories(data.memories || []);
    } catch {}
  }, []);

  const fetchSkills = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/memory-orchestrator/skill-list`);
      const data = await res.json();
      setSkills(data.skills || []);
    } catch {}
  }, []);

  const fetchExperiences = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/memory-orchestrator/experiences`);
      const data = await res.json();
      setExperiences(data.experiences || []);
    } catch {}
  }, []);

  const fetchNudges = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/memory-orchestrator/nudges`);
      const data = await res.json();
      setNudges(data.nudges || []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchMemories();
    fetchSkills();
    fetchExperiences();
    fetchNudges();
    const interval = setInterval(() => fetchStats(), 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchMemories, fetchSkills, fetchExperiences, fetchNudges]);

  const handleStoreMemory = async () => {
    if (!memoryContent.trim()) { showMessage('Memory content is required', 'error'); return; }
    try {
      const tags = memoryTags ? memoryTags.split(',').map(t => t.trim()).filter(Boolean) : [];
      const res = await fetch(`${apiBase}/memory-orchestrator/store-memory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: memoryContent,
          category: memoryCategory,
          priority: memoryPriority,
          tags,
          ttl: parseFloat(memoryTTL) || undefined,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setMemories(prev => [...prev, data]);
      setMemoryContent('');
      setMemoryTags('');
      showMessage(`Memory "${data.memory_id}" stored`, 'success');
      fetchStats();
    } catch {
      const simulated: MemoryEntry = {
        memory_id: uid(), category: memoryCategory, priority: memoryPriority,
        content: memoryContent, context: {}, tags: memoryTags ? memoryTags.split(',').map(t => t.trim()).filter(Boolean) : [],
        embedding_hash: '', access_count: 0, last_accessed: 0,
        created_at: Date.now() / 1000, expires_at: Date.now() / 1000 + parseFloat(memoryTTL),
        linked_memories: [], confidence_score: 1.0,
      };
      setMemories(prev => [...prev, simulated]);
      setMemoryContent('');
      setMemoryTags('');
      showMessage('Memory stored (simulated offline)', 'info');
    }
  };

  const handleRetrieveMemories = async () => {
    try {
      const queryTags = retrieveTags ? retrieveTags.split(',').map(t => t.trim()).filter(Boolean) : [];
      const res = await fetch(`${apiBase}/memory-orchestrator/retrieve-memories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_tags: queryTags.length > 0 ? queryTags : undefined,
          category: retrieveCategory || undefined,
          priority: retrievePriority || undefined,
          min_confidence: parseFloat(retrieveMinConfidence) || 0.5,
          limit: parseInt(retrieveLimit) || 50,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setRetrievedMemories(data.memories || []);
      showMessage(`Retrieved ${(data.memories || []).length} memories`, 'success');
    } catch {
      showMessage('Retrieval failed (offline)', 'info');
    }
  };

  const handleCreateSkill = async () => {
    if (!skillName.trim()) { showMessage('Skill name is required', 'error'); return; }
    try {
      const triggers = skillTriggers ? skillTriggers.split(',').map(t => t.trim()).filter(Boolean) : [];
      const preconds = skillPreconditions ? skillPreconditions.split(',').map(t => t.trim()).filter(Boolean) : [];
      const postconds = skillPostconditions ? skillPostconditions.split(',').map(t => t.trim()).filter(Boolean) : [];
      const res = await fetch(`${apiBase}/memory-orchestrator/create-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: skillName,
          description: skillDescription,
          trigger_patterns: triggers.length > 0 ? triggers : undefined,
          preconditions: preconds.length > 0 ? preconds : undefined,
          postconditions: postconds.length > 0 ? postconds : undefined,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setSkills(prev => [...prev, data]);
      setSkillName('');
      setSkillDescription('');
      setSkillTriggers('');
      setSkillPreconditions('');
      setSkillPostconditions('');
      showMessage(`Skill "${data.name}" created`, 'success');
      fetchStats();
    } catch {
      const simulated: SkillDefinition = {
        skill_id: uid(), name: skillName, description: skillDescription,
        version: 1, status: 'draft',
        trigger_patterns: skillTriggers ? skillTriggers.split(',').map(t => t.trim()).filter(Boolean) : [],
        action_sequence: [], preconditions: skillPreconditions ? skillPreconditions.split(',').map(t => t.trim()).filter(Boolean) : [],
        postconditions: skillPostconditions ? skillPostconditions.split(',').map(t => t.trim()).filter(Boolean) : [],
        success_rate: 0, usage_count: 0, improvement_history: [],
        created_at: Date.now() / 1000, updated_at: 0,
        parent_skill_id: '', derived_skills: [],
      };
      setSkills(prev => [...prev, simulated]);
      setSkillName('');
      setSkillDescription('');
      setSkillTriggers('');
      setSkillPreconditions('');
      setSkillPostconditions('');
      showMessage('Skill created (simulated offline)', 'info');
    }
  };

  const handleImproveSkill = async () => {
    if (!improveSkillId) { showMessage('Select a skill to improve', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/memory-orchestrator/improve-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_id: improveSkillId,
          success: improveSuccess,
          improvement_notes: improveNotes,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setSkills(prev => prev.map(s => s.skill_id === improveSkillId ? data : s));
      setImproveSkillId('');
      setImproveNotes('');
      showMessage(`Skill "${data.name}" improved (v${data.version}, rate: ${(data.success_rate * 100).toFixed(0)}%)`, 'success');
      fetchStats();
    } catch {
      const skill = skills.find(s => s.skill_id === improveSkillId);
      if (skill) {
        const updated = {
          ...skill,
          usage_count: skill.usage_count + 1,
          success_rate: improveSuccess
            ? (skill.success_rate * skill.usage_count + 1) / (skill.usage_count + 1)
            : (skill.success_rate * skill.usage_count) / (skill.usage_count + 1),
          updated_at: Date.now() / 1000,
        };
        setSkills(prev => prev.map(s => s.skill_id === improveSkillId ? updated : s));
      }
      setImproveSkillId('');
      setImproveNotes('');
      showMessage('Skill improved (simulated offline)', 'info');
    }
  };

  const handleRecordExperience = async () => {
    if (!expSessionId.trim() || !expSummary.trim()) { showMessage('Session ID and summary are required', 'error'); return; }
    try {
      const lessons = expLessons ? expLessons.split(',').map(t => t.trim()).filter(Boolean) : [];
      const res = await fetch(`${apiBase}/memory-orchestrator/record-experience`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: expSessionId,
          summary: expSummary,
          lessons: lessons.length > 0 ? lessons : undefined,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      setExperiences(prev => [...prev, data]);
      setExpSessionId('');
      setExpSummary('');
      setExpLessons('');
      showMessage(`Experience recorded (score: ${data.consolidation_score?.toFixed(2)})`, 'success');
      fetchStats();
    } catch {
      const simulated: ExperienceRecord = {
        experience_id: uid(), session_id: expSessionId, summary: expSummary,
        extracted_patterns: [], lessons_learned: expLessons ? expLessons.split(',').map(t => t.trim()).filter(Boolean) : [],
        skill_improvements: [], memory_links: [],
        timestamp: Date.now() / 1000,
        consolidation_score: 0.3 + Math.random() * 0.5,
      };
      setExperiences(prev => [...prev, simulated]);
      setExpSessionId('');
      setExpSummary('');
      setExpLessons('');
      showMessage('Experience recorded (simulated offline)', 'info');
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: { background: '#1a1a2e', color: '#e0e0e0', padding: 20, borderRadius: 8, fontFamily: 'monospace' },
    header: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#e94560' },
    tabs: { display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' },
    tab: { padding: '8px 16px', borderRadius: '6px 6px 0 0', border: 'none', cursor: 'pointer', fontSize: 13, background: '#2a2a4a', color: '#aab' },
    tabActive: { background: '#3a3a6a', color: '#e94560', fontWeight: 'bold' },
    card: { background: '#16213e', borderRadius: 8, padding: 16, marginBottom: 12 },
    cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#e94560', marginBottom: 8 },
    input: { background: '#1a1a3a', border: '1px solid #1e1e1e', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' },
    select: { background: '#1a1a3a', border: '1px solid #1e1e1e', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13 },
    textarea: { background: '#1a1a3a', border: '1px solid #1e1e1e', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box', minHeight: 60, resize: 'vertical', fontFamily: 'monospace' },
    btn: { background: '#e94560', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 'bold' },
    btnSecondary: { background: '#1e1e1e', color: '#aab', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
    row: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 },
    label: { fontSize: 12, color: '#889', marginBottom: 4 },
    value: { fontSize: 14, color: '#e0e0e0', fontWeight: 'bold' },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 'bold' },
    msgSuccess: { background: '#1a4a1a', color: '#4caf50', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgError: { background: '#4a1a1a', color: '#f44336', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgInfo: { background: '#1a2a4a', color: '#7c9aff', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    checkbox: { marginRight: 6, accentColor: '#e94560' },
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      short_term: '#e94560', long_term: '#1e1e1e', episodic: '#f97316',
      semantic: '#e94560', procedural: '#1a1a2e',
    };
    return colors[category] || '#2a2a5a';
  };

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      critical: '#e94560', high: '#f97316', medium: '#eab308', low: '#4caf50', transient: '#889',
    };
    return colors[priority] || '#2a2a5a';
  };

  const getSkillStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: '#889', active: '#4caf50', improving: '#eab308', deprecated: '#f97316', archived: '#e94560',
    };
    return colors[status] || '#2a2a5a';
  };

  const renderStats = () => (
    <div>
      {stats && (
        <div style={{ ...styles.card, background: '#1e1e1e' }}>
          <div style={styles.cardTitle}>Memory Orchestrator Statistics</div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>Memories</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.memory?.total_memories}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>Total Stored</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.memory?.total_stored?.toLocaleString()}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>Skills</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.skills?.total_skills}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>Experiences</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.total_experiences}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>Nudges</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.total_nudges}</div>
            </div>
            <div style={{ textAlign: 'center', minWidth: 80 }}>
              <div style={styles.label}>Nudges Triggered</div>
              <div style={{ ...styles.value, color: '#f97316' }}>{stats.total_nudges_triggered}</div>
            </div>
          </div>
          {stats.memory?.by_category && (
            <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {Object.entries(stats.memory.by_category).map(([cat, count]) => (
                <span key={cat} style={{ ...styles.badge, background: '#1a1a3a', color: getCategoryColor(cat) }}>
                  {cat}: {count}
                </span>
              ))}
            </div>
          )}
          {stats.skills?.by_status && (
            <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {Object.entries(stats.skills.by_status).map(([status, count]) => (
                <span key={status} style={{ ...styles.badge, background: '#1a1a3a', color: getSkillStatusColor(status) }}>
                  {status}: {count}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderMemoriesTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Store Memory</div>
        <div style={styles.row}>
          <textarea
            style={styles.textarea}
            placeholder="Memory content..."
            value={memoryContent}
            onChange={e => setMemoryContent(e.target.value)}
          />
        </div>
        <div style={styles.row}>
          <select style={styles.select} value={memoryCategory} onChange={e => setMemoryCategory(e.target.value)}>
            {MEMORY_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <select style={styles.select} value={memoryPriority} onChange={e => setMemoryPriority(e.target.value)}>
            {MEMORY_PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <input style={{ ...styles.input, width: 150 }} placeholder="Tags (comma-separated)" value={memoryTags} onChange={e => setMemoryTags(e.target.value)} />
          <input style={{ ...styles.input, width: 100 }} placeholder="TTL (seconds)" value={memoryTTL} onChange={e => setMemoryTTL(e.target.value)} type="number" min="60" />
          <button style={styles.btn} onClick={handleStoreMemory}>Store Memory</button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Retrieve Memories</div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 200 }} placeholder="Tags (comma-separated)" value={retrieveTags} onChange={e => setRetrieveTags(e.target.value)} />
          <select style={styles.select} value={retrieveCategory} onChange={e => setRetrieveCategory(e.target.value)}>
            <option value="">Any Category</option>
            {MEMORY_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <select style={styles.select} value={retrievePriority} onChange={e => setRetrievePriority(e.target.value)}>
            <option value="">Any Priority</option>
            {MEMORY_PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 120 }} placeholder="Min Confidence" value={retrieveMinConfidence} onChange={e => setRetrieveMinConfidence(e.target.value)} type="number" min="0" max="1" step="0.1" />
          <input style={{ ...styles.input, width: 80 }} placeholder="Limit" value={retrieveLimit} onChange={e => setRetrieveLimit(e.target.value)} type="number" min="1" max="200" />
          <button style={styles.btn} onClick={handleRetrieveMemories}>Search</button>
        </div>
        {retrievedMemories.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ color: '#889', fontSize: 12, marginBottom: 8 }}>{retrievedMemories.length} results</div>
            <div style={styles.grid}>
              {retrievedMemories.map(mem => (
                <div key={mem.memory_id} style={{ ...styles.card, background: '#1a1a3a', borderLeft: `4px solid ${getPriorityColor(mem.priority)}` }}>
                  <div style={{ fontSize: 12, color: '#889', marginBottom: 4, wordBreak: 'break-all' }}>{mem.memory_id}</div>
                  <div style={{ fontSize: 13, marginBottom: 8, color: '#ccc' }}>{mem.content.length > 120 ? mem.content.slice(0, 120) + '...' : mem.content}</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    <span style={{ ...styles.badge, background: getCategoryColor(mem.category), color: '#fff' }}>{mem.category}</span>
                    <span style={{ ...styles.badge, background: getPriorityColor(mem.priority), color: '#fff' }}>{mem.priority}</span>
                    <span style={{ ...styles.badge, background: '#1a1a3a' }}>conf: {mem.confidence_score.toFixed(2)}</span>
                    <span style={{ ...styles.badge, background: '#1a1a3a' }}>accessed: {mem.access_count}x</span>
                  </div>
                  {mem.tags.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                      {mem.tags.map(tag => (
                        <span key={tag} style={{ ...styles.badge, background: '#1e1e1e', fontSize: 10 }}>{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>All Memories ({memories.length})</div>
        {memories.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No memories stored yet.</div>}
        <div style={styles.grid}>
          {memories.map(mem => (
            <div key={mem.memory_id} style={{ ...styles.card, background: '#1a1a3a', borderLeft: `4px solid ${getCategoryColor(mem.category)}` }}>
              <div style={{ fontSize: 12, color: '#889', marginBottom: 4, wordBreak: 'break-all' }}>{mem.memory_id}</div>
              <div style={{ fontSize: 13, marginBottom: 8, color: '#ccc' }}>{mem.content.length > 100 ? mem.content.slice(0, 100) + '...' : mem.content}</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                <span style={{ ...styles.badge, background: getCategoryColor(mem.category), color: '#fff' }}>{mem.category}</span>
                <span style={{ ...styles.badge, background: getPriorityColor(mem.priority), color: '#fff' }}>{mem.priority}</span>
              </div>
              <div style={{ fontSize: 11, color: '#667', marginTop: 4 }}>
                Confidence: {mem.confidence_score.toFixed(2)} | Accessed: {mem.access_count}x
                {mem.tags.length > 0 && <span> | Tags: {mem.tags.join(', ')}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderSkillsTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Create Skill</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Skill name" value={skillName} onChange={e => setSkillName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <textarea
            style={styles.textarea}
            placeholder="Description..."
            value={skillDescription}
            onChange={e => setSkillDescription(e.target.value)}
          />
        </div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Trigger patterns (comma-separated)" value={skillTriggers} onChange={e => setSkillTriggers(e.target.value)} />
        </div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Preconditions (comma-separated)" value={skillPreconditions} onChange={e => setSkillPreconditions(e.target.value)} />
          <input style={styles.input} placeholder="Postconditions (comma-separated)" value={skillPostconditions} onChange={e => setSkillPostconditions(e.target.value)} />
        </div>
        <button style={styles.btn} onClick={handleCreateSkill}>Create Skill</button>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Improve Skill</div>
        <div style={styles.row}>
          <select style={styles.select} value={improveSkillId} onChange={e => setImproveSkillId(e.target.value)}>
            <option value="">-- Select Skill --</option>
            {skills.filter(s => s.status !== 'archived').map(s => <option key={s.skill_id} value={s.skill_id}>{s.name} (v{s.version})</option>)}
          </select>
          <label style={{ fontSize: 13, color: '#ccc', display: 'flex', alignItems: 'center' }}>
            <input type="checkbox" checked={improveSuccess} onChange={e => setImproveSuccess(e.target.checked)} style={styles.checkbox} />
            Success
          </label>
          <input style={{ ...styles.input, width: 200 }} placeholder="Improvement notes" value={improveNotes} onChange={e => setImproveNotes(e.target.value)} />
          <button style={styles.btn} onClick={handleImproveSkill} disabled={!improveSkillId}>Improve</button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Skills ({skills.length})</div>
        {skills.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No skills created yet.</div>}
        <div style={styles.grid}>
          {skills.map(skill => (
            <div key={skill.skill_id} style={{ ...styles.card, background: '#1a1a3a', borderLeft: `4px solid ${getSkillStatusColor(skill.status)}` }}>
              <div style={styles.cardTitle}>{skill.name} <span style={{ fontSize: 11, color: '#889' }}>v{skill.version}</span></div>
              <div style={{ fontSize: 12, color: '#889', marginBottom: 8 }}>{skill.description || 'No description'}</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 4 }}>
                <span style={{ ...styles.badge, background: getSkillStatusColor(skill.status), color: '#fff' }}>{skill.status}</span>
                <span style={{ ...styles.badge, background: '#1a1a3a' }}>success: {(skill.success_rate * 100).toFixed(0)}%</span>
                <span style={{ ...styles.badge, background: '#1a1a3a' }}>used: {skill.usage_count}x</span>
              </div>
              {skill.trigger_patterns.length > 0 && (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                  {skill.trigger_patterns.map((p, i) => (
                    <span key={i} style={{ ...styles.badge, background: '#1e1e1e', fontSize: 10 }}>{p}</span>
                  ))}
                </div>
              )}
              {skill.improvement_history.length > 0 && (
                <div style={{ fontSize: 11, color: '#667', marginTop: 4 }}>
                  Improvements: {skill.improvement_history.length}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderExperiencesTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Record Experience</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Session ID" value={expSessionId} onChange={e => setExpSessionId(e.target.value)} />
        </div>
        <div style={styles.row}>
          <textarea
            style={styles.textarea}
            placeholder="Experience summary..."
            value={expSummary}
            onChange={e => setExpSummary(e.target.value)}
          />
        </div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Lessons learned (comma-separated)" value={expLessons} onChange={e => setExpLessons(e.target.value)} />
          <button style={styles.btn} onClick={handleRecordExperience}>Record</button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Experiences ({experiences.length})</div>
        {experiences.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No experiences recorded yet.</div>}
        <div style={styles.grid}>
          {experiences.map(exp => (
            <div key={exp.experience_id} style={{ ...styles.card, background: '#1a1a3a', borderLeft: `4px solid ${exp.consolidation_score >= 0.6 ? '#4caf50' : '#eab308'}` }}>
              <div style={{ fontSize: 12, color: '#889', marginBottom: 4 }}>Session: {exp.session_id}</div>
              <div style={{ fontSize: 13, marginBottom: 8, color: '#ccc' }}>{exp.summary.length > 150 ? exp.summary.slice(0, 150) + '...' : exp.summary}</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                <span style={{ ...styles.badge, background: exp.consolidation_score >= 0.6 ? '#1a4a1a' : '#3a3a1a', color: exp.consolidation_score >= 0.6 ? '#4caf50' : '#eab308' }}>
                  consolidation: {exp.consolidation_score.toFixed(2)}
                </span>
              </div>
              {exp.lessons_learned.length > 0 && (
                <div style={{ marginTop: 6 }}>
                  <div style={{ fontSize: 11, color: '#889', marginBottom: 4 }}>Lessons:</div>
                  {exp.lessons_learned.map((lesson, i) => (
                    <div key={i} style={{ fontSize: 11, color: '#aab', paddingLeft: 8 }}>• {lesson}</div>
                  ))}
                </div>
              )}
              {exp.extracted_patterns.length > 0 && (
                <div style={{ marginTop: 4 }}>
                  <span style={{ ...styles.badge, background: '#1e1e1e', fontSize: 10 }}>
                    {exp.extracted_patterns.length} patterns
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderNudgesTab = () => (
    <div>
      {stats && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Nudge Statistics</div>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', fontSize: 13 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={styles.label}>Total Nudges</div>
              <div style={{ ...styles.value, color: '#e94560' }}>{stats.total_nudges}</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={styles.label}>Total Triggered</div>
              <div style={{ ...styles.value, color: '#f97316' }}>{stats.total_nudges_triggered}</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={styles.label}>Experiences Recorded</div>
              <div style={{ ...styles.value, color: '#4caf50' }}>{stats.total_experiences_recorded}</div>
            </div>
          </div>
        </div>
      )}

      <div style={styles.card}>
        <div style={styles.cardTitle}>Nudge Schedules ({nudges.length})</div>
        {nudges.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No nudge schedules configured.</div>}
        <div style={styles.grid}>
          {nudges.map(nudge => (
            <div key={nudge.nudge_id} style={{ ...styles.card, background: '#1a1a3a', borderLeft: `4px solid ${nudge.enabled ? '#4caf50' : '#e94560'}` }}>
              <div style={{ fontSize: 12, color: '#889', marginBottom: 4 }}>{nudge.nudge_id}</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                <span style={{ ...styles.badge, background: '#1e1e1e' }}>{nudge.trigger_type}</span>
                <span style={{ ...styles.badge, background: nudge.enabled ? '#1a4a1a' : '#4a1a1a', color: nudge.enabled ? '#4caf50' : '#f44336' }}>
                  {nudge.enabled ? 'enabled' : 'disabled'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#889' }}>
                <div>Interval: {nudge.interval_seconds}s</div>
                <div>Triggered: {nudge.trigger_count}{nudge.max_triggers > 0 ? ` / ${nudge.max_triggers}` : ''}</div>
                {nudge.last_triggered > 0 && <div>Last: {new Date(nudge.last_triggered * 1000).toLocaleString()}</div>}
                {nudge.next_trigger > 0 && <div>Next: {new Date(nudge.next_trigger * 1000).toLocaleString()}</div>}
              </div>
              {nudge.target_memory_ids.length > 0 && (
                <div style={{ fontSize: 11, color: '#667', marginTop: 4 }}>
                  Target memories: {nudge.target_memory_ids.length}
                </div>
              )}
              {nudge.target_skill_ids.length > 0 && (
                <div style={{ fontSize: 11, color: '#667' }}>
                  Target skills: {nudge.target_skill_ids.length}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: 'memories', label: 'Memories', icon: '🧠' },
    { id: 'skills', label: 'Skills', icon: '⚡' },
    { id: 'experiences', label: 'Experiences', icon: '📖' },
    { id: 'nudges', label: 'Nudges', icon: '🔔' },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case 'memories': return renderMemoriesTab();
      case 'skills': return renderSkillsTab();
      case 'experiences': return renderExperiencesTab();
      case 'nudges': return renderNudgesTab();
      default: return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>🧠 Memory Orchestrator</div>
      {message && (
        <div style={message.type === 'success' ? styles.msgSuccess : message.type === 'error' ? styles.msgError : styles.msgInfo}>
          {message.text}
        </div>
      )}
      {renderStats()}
      <div style={styles.tabs}>
        {TAB_CONFIG.map(tab => (
          <button
            key={tab.id}
            style={{ ...styles.tab, ...(activeTab === tab.id ? styles.tabActive : {}) }}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>
      {renderTabContent(activeTab)}
    </div>
  );
};

export default MemoryOrchestratorPanel;