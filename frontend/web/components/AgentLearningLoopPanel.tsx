import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type SkillCategory = 'reasoning' | 'tool_use' | 'communication' | 'planning' | 'memory';
type SkillState = 'acquired' | 'practicing' | 'mastered' | 'dormant';
type MemoryType = 'episodic' | 'semantic' | 'procedural';
type SessionStatus = 'running' | 'paused' | 'completed' | 'aborted';
type NudgePriority = 'low' | 'medium' | 'high' | 'critical';

interface Skill {
  id: string;
  name: string;
  state: SkillState;
  category: SkillCategory;
  level: number;
  xp: number;
  last_practiced: string;
  description: string;
}

interface MemoryEntry {
  id: string;
  type: MemoryType;
  content: string;
  importance: number;
  created_at: string;
  tags: string[];
}

interface LearningSession {
  id: string;
  name: string;
  status: SessionStatus;
  focus_skill: string;
  progress: number;
  started_at: string;
  duration: string;
}

interface Nudge {
  id: string;
  priority: NudgePriority;
  message: string;
  related_skill: string;
  created_at: string;
  action_label: string;
}

interface LoopStats {
  total_skills: number;
  mastered_skills: number;
  total_memories: number;
  active_sessions: number;
  pending_nudges: number;
}

interface SkillEvolutionEntry {
  skill_name: string;
  level: number;
  xp: number;
  timestamp: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SKILL_CATEGORY_LABELS: Record<SkillCategory, string> = {
  reasoning: 'Reasoning',
  tool_use: 'Tool Use',
  communication: 'Communication',
  planning: 'Planning',
  memory: 'Memory',
};

const SKILL_STATE_COLORS: Record<SkillState, string> = {
  acquired: '#74b9ff',
  practicing: '#fdcb6e',
  mastered: '#6bcb77',
  dormant: '#888',
};

const MEMORY_TYPE_COLORS: Record<MemoryType, string> = {
  episodic: '#a29bfe',
  semantic: '#00b894',
  procedural: '#fdcb6e',
};

const SESSION_STATUS_COLORS: Record<SessionStatus, string> = {
  running: '#6bcb77',
  paused: '#fdcb6e',
  completed: '#74b9ff',
  aborted: '#ff6b6b',
};

const NUDGE_PRIORITY_COLORS: Record<NudgePriority, string> = {
  low: '#888',
  medium: '#fdcb6e',
  high: '#e17055',
  critical: '#ff6b6b',
};

const AgentLearningLoopPanel: React.FC = () => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [sessions, setSessions] = useState<LearningSession[]>([]);
  const [nudges, setNudges] = useState<Nudge[]>([]);
  const [stats, setStats] = useState<LoopStats | null>(null);
  const [evolution, setEvolution] = useState<SkillEvolutionEntry[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<'skills' | 'memories' | 'sessions' | 'nudges'>('skills');

  const apiBase = API_ROOT + '/agent';

  const defaultSkills: Skill[] = [
    { id: uid(), name: 'Context Analysis', state: 'mastered', category: 'reasoning', level: 5, xp: 940, last_practiced: '2m ago', description: 'Analyze and decompose complex user contexts' },
    { id: uid(), name: 'Code Generation', state: 'practicing', category: 'tool_use', level: 3, xp: 520, last_practiced: '15m ago', description: 'Generate high-quality code snippets across languages' },
    { id: uid(), name: 'Tone Calibration', state: 'acquired', category: 'communication', level: 2, xp: 210, last_practiced: '1h ago', description: 'Adjust communication tone based on context' },
    { id: uid(), name: 'Task Decomposition', state: 'mastered', category: 'planning', level: 4, xp: 780, last_practiced: '5m ago', description: 'Break complex tasks into manageable subtasks' },
    { id: uid(), name: 'Memory Retrieval', state: 'practicing', category: 'memory', level: 3, xp: 430, last_practiced: '30m ago', description: 'Efficiently retrieve relevant past interactions' },
    { id: uid(), name: 'Error Recovery', state: 'dormant', category: 'reasoning', level: 2, xp: 180, last_practiced: '3h ago', description: 'Recover gracefully from execution errors' },
  ];

  const defaultMemories: MemoryEntry[] = [
    { id: uid(), type: 'episodic', content: 'User requested a Python refactoring task for the inventory module', importance: 0.8, created_at: '10m ago', tags: ['python', 'refactoring'] },
    { id: uid(), type: 'semantic', content: 'Project uses TypeScript with strict mode enabled', importance: 0.9, created_at: '1h ago', tags: ['typescript', 'config'] },
    { id: uid(), type: 'procedural', content: 'Deployment pipeline: lint → test → build → deploy', importance: 0.7, created_at: '2h ago', tags: ['devops', 'pipeline'] },
    { id: uid(), type: 'episodic', content: 'Debugged a race condition in the WebSocket handler', importance: 0.85, created_at: '30m ago', tags: ['debugging', 'websocket'] },
  ];

  const defaultSessions: LearningSession[] = [
    { id: uid(), name: 'Sprint 42 Review', status: 'running', focus_skill: 'Task Decomposition', progress: 67, started_at: '1h ago', duration: '45m' },
    { id: uid(), name: 'Code Quality Drill', status: 'paused', focus_skill: 'Code Generation', progress: 42, started_at: '3h ago', duration: '22m' },
    { id: uid(), name: 'Context Mastery', status: 'completed', focus_skill: 'Context Analysis', progress: 100, started_at: '1d ago', duration: '1h 10m' },
  ];

  const defaultNudges: Nudge[] = [
    { id: uid(), priority: 'high', message: 'Review your error recovery logs — 3 recent failures need attention', related_skill: 'Error Recovery', created_at: '15m ago', action_label: 'Review Now' },
    { id: uid(), priority: 'medium', message: 'Code Generation skill is ready for level-up assessment', related_skill: 'Code Generation', created_at: '1h ago', action_label: 'Start Assessment' },
    { id: uid(), priority: 'low', message: 'Consider revisiting dormant Tone Calibration practice', related_skill: 'Tone Calibration', created_at: '3h ago', action_label: 'Practice' },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchLoopStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/learning-loop/stats`);
      const data = await res.json();
      setStats(data);
    } catch {
      setStats({
        total_skills: 6,
        mastered_skills: 2,
        total_memories: 4,
        active_sessions: 2,
        pending_nudges: 3,
      });
    }
  }, []);

  const fetchSkillEvolution = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/learning-loop/skill-evolution`);
      const data = await res.json();
      setEvolution(data.evolution || data);
    } catch {
      setEvolution([
        { skill_name: 'Context Analysis', level: 5, xp: 940, timestamp: Date.now() - 10000 },
        { skill_name: 'Code Generation', level: 3, xp: 520, timestamp: Date.now() - 20000 },
        { skill_name: 'Task Decomposition', level: 4, xp: 780, timestamp: Date.now() - 5000 },
      ]);
    }
  }, []);

  const fetchMemories = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/learning-loop/retrieve-memories`);
      const data = await res.json();
      setMemories(data.memories || data);
    } catch {}
  }, []);

  const fetchNudges = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/learning-loop/pending-nudges`);
      const data = await res.json();
      setNudges(data.nudges || data);
    } catch {}
  }, []);

  useEffect(() => {
    setSkills(defaultSkills);
    setMemories(defaultMemories);
    setSessions(defaultSessions);
    setNudges(defaultNudges);
    fetchLoopStats();
    fetchSkillEvolution();
    fetchMemories();
    fetchNudges();
  }, [fetchLoopStats, fetchSkillEvolution, fetchMemories, fetchNudges]);

  const handleCreateSkill = async () => {
    try {
      const res = await fetch(`${apiBase}/learning-loop/create-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'New Skill', category: 'reasoning' }),
      });
      const data = await res.json();
      const newSkill: Skill = {
        id: data.id || uid(),
        name: data.name || 'New Skill',
        state: 'acquired',
        category: data.category || 'reasoning',
        level: 1,
        xp: 0,
        last_practiced: 'just now',
        description: data.description || 'Newly created skill',
      };
      setSkills(prev => [newSkill, ...prev]);
      showMessage('Skill created successfully', 'success');
    } catch {
      const newSkill: Skill = {
        id: uid(),
        name: 'New Skill',
        state: 'acquired',
        category: 'reasoning',
        level: 1,
        xp: 0,
        last_practiced: 'just now',
        description: 'Newly created skill',
      };
      setSkills(prev => [newSkill, ...prev]);
      showMessage('Skill created (offline mode)', 'info');
    }
  };

  const handleRecordMemory = async () => {
    try {
      const res = await fetch(`${apiBase}/learning-loop/record-memory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'episodic', content: 'New interaction recorded', tags: [] }),
      });
      const data = await res.json();
      const entry: MemoryEntry = {
        id: data.id || uid(),
        type: data.type || 'episodic',
        content: data.content || 'New interaction recorded',
        importance: data.importance || 0.5,
        created_at: 'just now',
        tags: data.tags || [],
      };
      setMemories(prev => [entry, ...prev]);
      showMessage('Memory recorded', 'success');
    } catch {
      const entry: MemoryEntry = {
        id: uid(),
        type: 'episodic',
        content: 'New interaction recorded',
        importance: 0.5,
        created_at: 'just now',
        tags: [],
      };
      setMemories(prev => [entry, ...prev]);
      showMessage('Memory recorded (offline mode)', 'info');
    }
  };

  const handleStartSession = async () => {
    try {
      const res = await fetch(`${apiBase}/learning-loop/start-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'New Session', focus_skill: '' }),
      });
      const data = await res.json();
      const session: LearningSession = {
        id: data.id || uid(),
        name: data.name || 'New Session',
        status: 'running',
        focus_skill: data.focus_skill || 'General',
        progress: 0,
        started_at: 'just now',
        duration: '0m',
      };
      setSessions(prev => [session, ...prev]);
      showMessage('Learning session started', 'success');
    } catch {
      const session: LearningSession = {
        id: uid(),
        name: 'New Session',
        status: 'running',
        focus_skill: 'General',
        progress: 0,
        started_at: 'just now',
        duration: '0m',
      };
      setSessions(prev => [session, ...prev]);
      showMessage('Learning session started (offline mode)', 'info');
    }
  };

  const handleDismissNudge = async (nudgeId: string) => {
    try {
      await fetch(`${apiBase}/learning-loop/dismiss-nudge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nudge_id: nudgeId }),
      });
      setNudges(prev => prev.filter(n => n.id !== nudgeId));
      showMessage('Nudge dismissed', 'info');
    } catch {
      setNudges(prev => prev.filter(n => n.id !== nudgeId));
      showMessage('Nudge dismissed (offline mode)', 'info');
    }
  };

  const handleRefresh = async () => {
    await Promise.all([fetchLoopStats(), fetchSkillEvolution(), fetchMemories(), fetchNudges()]);
    showMessage('Learning loop refreshed', 'info');
  };

  const tabItems: { key: typeof activeTab; label: string; icon: string; count: number }[] = [
    { key: 'skills', label: 'Skills', icon: '\uD83E\uDDE0', count: skills.length },
    { key: 'memories', label: 'Memories', icon: '\uD83D\uDCDD', count: memories.length },
    { key: 'sessions', label: 'Sessions', icon: '\uD83C\uDFAF', count: sessions.length },
    { key: 'nudges', label: 'Nudges', icon: '\uD83D\uDD14', count: nudges.length },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>{'\uD83E\uDDE0'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Learning Loop</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.mastered_skills}/{stats.total_skills} mastered | {stats.active_sessions} active
            </span>
          )}
          <button onClick={handleRefresh} style={{
            background: 'none', border: '1px solid #333', color: '#aaa',
            borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 11,
          }}>
            <i className="fa-solid fa-rotate" />
          </button>
        </div>
      </div>

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

      <div style={{ padding: '10px 12px', display: 'flex', gap: 6, borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap' }}>
        <button onClick={handleCreateSkill} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#74b9ff',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83E\uDDE0'} Create Skill
        </button>
        <button onClick={handleRecordMemory} style={{
          padding: '6px 12px', backgroundColor: '#2d3a5a', color: '#a29bfe',
          border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83D\uDCDD'} Record Memory
        </button>
        <button onClick={handleStartSession} style={{
          padding: '6px 12px', backgroundColor: '#2d4a3a', color: '#6bcb77',
          border: '1px solid #3d5a4a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600,
        }}>
          {'\uD83C\uDFAF'} Start Session
        </button>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600,
            backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent',
            color: activeTab === tab.key ? '#e0e0e0' : '#888',
            border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent',
            cursor: 'pointer',
          }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'skills' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {evolution.length > 0 && (
              <div style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e', marginBottom: 4,
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#aaa' }}>{'\uD83D\uDCC8'} Skill Evolution</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {evolution.slice(0, 4).map(ev => (
                    <div key={ev.skill_name} style={{
                      padding: '6px 10px', backgroundColor: '#141428', borderRadius: 4,
                      fontSize: 10, display: 'flex', alignItems: 'center', gap: 6,
                    }}>
                      <span style={{ color: '#ccc' }}>{ev.skill_name}</span>
                      <span style={{ color: '#6bcb77', fontWeight: 600 }}>Lv.{ev.level}</span>
                      <span style={{ color: '#888' }}>{ev.xp} XP</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {skills.map(skill => (
              <div key={skill.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${SKILL_STATE_COLORS[skill.state]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{skill.name}</span>
                      <span style={{
                        fontSize: 9, padding: '1px 6px', borderRadius: 3,
                        backgroundColor: SKILL_STATE_COLORS[skill.state] + '33',
                        color: SKILL_STATE_COLORS[skill.state], fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>{skill.state}</span>
                    </div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>{skill.description}</div>
                  </div>
                  <span style={{
                    fontSize: 9, padding: '2px 6px', borderRadius: 3,
                    backgroundColor: '#141428', color: '#aaa',
                  }}>{SKILL_CATEGORY_LABELS[skill.category]}</span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#666' }}>
                  <span>Level: <span style={{ color: '#aaa', fontWeight: 600 }}>{skill.level}</span></span>
                  <span>XP: <span style={{ color: '#aaa', fontWeight: 600 }}>{skill.xp}</span></span>
                  <span>Last: {skill.last_practiced}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'memories' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {memories.map(mem => (
              <div key={mem.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${MEMORY_TYPE_COLORS[mem.type]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: MEMORY_TYPE_COLORS[mem.type] + '33',
                    color: MEMORY_TYPE_COLORS[mem.type], fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{mem.type}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 10, color: '#666' }}>Importance: {(mem.importance * 100).toFixed(0)}%</span>
                    <span style={{ fontSize: 10, color: '#555' }}>{mem.created_at}</span>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: '#ccc', marginBottom: 6 }}>{mem.content}</div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {mem.tags.map(tag => (
                    <span key={tag} style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#888',
                    }}>#{tag}</span>
                  ))}
                </div>
              </div>
            ))}
            {memories.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDCDD'}</span>
                No memories recorded yet
              </div>
            )}
          </div>
        )}

        {activeTab === 'sessions' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sessions.map(session => (
              <div key={session.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${SESSION_STATUS_COLORS[session.status]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{session.name}</span>
                  <span style={{
                    fontSize: 9, padding: '1px 6px', borderRadius: 3,
                    backgroundColor: SESSION_STATUS_COLORS[session.status] + '33',
                    color: SESSION_STATUS_COLORS[session.status], fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>{session.status}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>
                  Focus: {session.focus_skill}
                </div>
                <div style={{
                  height: 4, backgroundColor: '#141428', borderRadius: 2, marginBottom: 6,
                }}>
                  <div style={{
                    height: '100%', width: `${session.progress}%`,
                    backgroundColor: session.status === 'completed' ? '#6bcb77' : '#6c5ce7',
                    borderRadius: 2,
                  }} />
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 10, color: '#666' }}>
                  <span>Duration: {session.duration}</span>
                  <span>Started: {session.started_at}</span>
                </div>
              </div>
            ))}
            {sessions.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83C\uDFAF'}</span>
                No active learning sessions
              </div>
            )}
          </div>
        )}

        {activeTab === 'nudges' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {nudges.map(nudge => (
              <div key={nudge.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${NUDGE_PRIORITY_COLORS[nudge.priority]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: NUDGE_PRIORITY_COLORS[nudge.priority] + '33',
                      color: NUDGE_PRIORITY_COLORS[nudge.priority], fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{nudge.priority}</span>
                    <span style={{ fontSize: 10, color: '#888' }}>Re: {nudge.related_skill}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#555' }}>{nudge.created_at}</span>
                </div>
                <div style={{ fontSize: 12, color: '#ccc', marginBottom: 8 }}>{nudge.message}</div>
                <button onClick={() => handleDismissNudge(nudge.id)} style={{
                  padding: '4px 10px', fontSize: 10,
                  backgroundColor: '#3a2a2a', color: '#ff6b6b',
                  border: '1px solid #5a3a3a', borderRadius: 3, cursor: 'pointer',
                }}>
                  {'\u2715'} {nudge.action_label}
                </button>
              </div>
            ))}
            {nudges.length === 0 && (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD14'}</span>
                No pending nudges
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          {'\uD83E\uDDE0'} {skills.length} skills · {memories.length} memories
        </span>
        <span>
          {stats ? `${stats.active_sessions || 0} sessions · ${stats.pending_nudges || 0} nudges` : 'Connected'}
        </span>
      </div>
    </div>
  );
};

export default AgentLearningLoopPanel;