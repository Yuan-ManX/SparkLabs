import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'generate' | 'compose' | 'trees';

interface SkillItem {
  id: string;
  name: string;
  category: string;
  description: string;
  level: number;
  cooldown: number;
  mana_cost: number;
  damage: number;
  effects: string[];
  created_at: number;
}

interface TemplateItem {
  id: string;
  name: string;
  category: string;
  base_stats: Record<string, number>;
  created_at: number;
}

interface SkillTreeItem {
  id: string;
  name: string;
  root_skill: string;
  nodes: SkillTreeNode[];
  created_at: number;
}

interface SkillTreeNode {
  id: string;
  name: string;
  parent_id: string | null;
  level_required: number;
  unlocks: string[];
  children: string[];
}

interface ComposedSkill {
  id: string;
  name: string;
  source_skills: string[];
  combined_effects: string[];
  power_level: number;
  synergy_score: number;
  created_at: number;
}

interface EvaluationResult {
  id: string;
  skill_name: string;
  score: number;
  balance_rating: string;
  metrics: Record<string, number>;
  feedback: string;
  evaluated_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SKILL_CATEGORIES = ['combat', 'magic', 'defense', 'support', 'utility', 'movement', 'summon', 'stealth', 'healing', 'elemental'];
const SKILL_EFFECTS = ['damage', 'heal', 'buff', 'debuff', 'stun', 'slow', 'dot', 'shield', 'teleport', 'invisible', 'taunt', 'cleanse'];
const METRIC_KEYS = ['damage_per_second', 'utility_score', 'cooldown_efficiency', 'mana_efficiency', 'crowd_control', 'survivability', 'burst_potential'];

const SkillGeneratorPanel: React.FC = () => {
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [skillTrees, setSkillTrees] = useState<SkillTreeItem[]>([]);
  const [composedSkills, setComposedSkills] = useState<ComposedSkill[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationResult[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('generate');

  const [skillName, setSkillName] = useState('');
  const [skillCategory, setSkillCategory] = useState('combat');
  const [skillLevel, setSkillLevel] = useState('1');
  const [skillPrompt, setSkillPrompt] = useState('');
  const [generatedSkill, setGeneratedSkill] = useState<SkillItem | null>(null);

  const [templateName, setTemplateName] = useState('');
  const [templateCategory, setTemplateCategory] = useState('combat');
  const [templateBaseDamage, setTemplateBaseDamage] = useState('50');
  const [templateBaseCooldown, setTemplateBaseCooldown] = useState('5');

  const [batchCount, setBatchCount] = useState('5');
  const [batchCategory, setBatchCategory] = useState('combat');

  const [selectedSkillId1, setSelectedSkillId1] = useState('');
  const [selectedSkillId2, setSelectedSkillId2] = useState('');
  const [composedSkillName, setComposedSkillName] = useState('');

  const [evaluateSkillId, setEvaluateSkillId] = useState('');
  const [lastEvaluation, setLastEvaluation] = useState<EvaluationResult | null>(null);

  const [treeName, setTreeName] = useState('');
  const [treeRootSkill, setTreeRootSkill] = useState('');
  const [treeDepth, setTreeDepth] = useState('4');
  const [treeBranches, setTreeBranches] = useState('3');

  const apiBase = API_ROOT + '/agent/skill-generator';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchSkills = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/skill-list`);
      const data = await res.json();
      setSkills(data.skills || []);
    } catch {}
  }, []);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/templates`);
      const data = await res.json();
      setTemplates(data.templates || []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchSkills();
    fetchTemplates();
    const interval = setInterval(() => {
      fetchSkills();
      fetchTemplates();
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchSkills, fetchTemplates]);

  const handleGenerateSkill = async () => {
    if (!skillName.trim()) { showMessage('Skill name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/generate-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: skillName,
          category: skillCategory,
          level: parseInt(skillLevel) || 1,
          prompt: skillPrompt || `Generate a ${skillCategory} skill named ${skillName}`,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const skill: SkillItem = {
        id: data.id || uid(),
        name: data.name || skillName,
        category: data.category || skillCategory,
        description: data.description || '',
        level: data.level || parseInt(skillLevel) || 1,
        cooldown: data.cooldown || 0,
        mana_cost: data.mana_cost || 0,
        damage: data.damage || 0,
        effects: data.effects || [],
        created_at: data.created_at || Date.now(),
      };
      setGeneratedSkill(skill);
      setSkills(prev => [...prev, skill]);
      showMessage(`Skill "${skill.name}" generated`, 'success');
    } catch {
      const skill: SkillItem = {
        id: uid(), name: skillName, category: skillCategory,
        description: `A powerful ${skillCategory} ability that deals ${Math.floor(Math.random() * 100) + 30} base damage.`,
        level: parseInt(skillLevel) || 1,
        cooldown: Math.floor(Math.random() * 10) + 2,
        mana_cost: Math.floor(Math.random() * 50) + 10,
        damage: Math.floor(Math.random() * 100) + 30,
        effects: SKILL_EFFECTS.sort(() => 0.5 - Math.random()).slice(0, Math.floor(Math.random() * 3) + 1),
        created_at: Date.now(),
      };
      setGeneratedSkill(skill);
      setSkills(prev => [...prev, skill]);
      showMessage(`Skill "${skillName}" simulated (offline)`, 'info');
    }
  };

  const handleCreateTemplate = async () => {
    if (!templateName.trim()) { showMessage('Template name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/create-template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: templateName,
          category: templateCategory,
          base_damage: parseInt(templateBaseDamage) || 50,
          base_cooldown: parseInt(templateBaseCooldown) || 5,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const template: TemplateItem = {
        id: data.id || uid(),
        name: data.name || templateName,
        category: data.category || templateCategory,
        base_stats: data.base_stats || {},
        created_at: data.created_at || Date.now(),
      };
      setTemplates(prev => [...prev, template]);
      setTemplateName('');
      showMessage(`Template "${template.name}" created`, 'success');
    } catch {
      const template: TemplateItem = {
        id: uid(), name: templateName, category: templateCategory,
        base_stats: {
          damage: parseInt(templateBaseDamage) || 50,
          cooldown: parseInt(templateBaseCooldown) || 5,
          mana_cost: Math.floor(Math.random() * 40) + 10,
          range: Math.floor(Math.random() * 20) + 5,
        },
        created_at: Date.now(),
      };
      setTemplates(prev => [...prev, template]);
      setTemplateName('');
      showMessage(`Template "${templateName}" simulated (offline)`, 'info');
    }
  };

  const handleBatchGenerate = async () => {
    try {
      const res = await fetch(`${apiBase}/batch-generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          count: parseInt(batchCount) || 5,
          category: batchCategory,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const batchSkills: SkillItem[] = (data.skills || []).map((s: any) => ({
        id: s.id || uid(),
        name: s.name,
        category: s.category || batchCategory,
        description: s.description || '',
        level: s.level || 1,
        cooldown: s.cooldown || 0,
        mana_cost: s.mana_cost || 0,
        damage: s.damage || 0,
        effects: s.effects || [],
        created_at: s.created_at || Date.now(),
      }));
      setSkills(prev => [...prev, ...batchSkills]);
      showMessage(`${batchSkills.length} skills batch-generated`, 'success');
    } catch {
      const count = parseInt(batchCount) || 5;
      const batchSkills: SkillItem[] = Array.from({ length: count }, (_, i) => ({
        id: uid(),
        name: `${batchCategory}_skill_${i + 1}`,
        category: batchCategory,
        description: `Auto-generated ${batchCategory} skill #${i + 1}.`,
        level: Math.floor(Math.random() * 5) + 1,
        cooldown: Math.floor(Math.random() * 10) + 2,
        mana_cost: Math.floor(Math.random() * 50) + 10,
        damage: Math.floor(Math.random() * 100) + 20,
        effects: SKILL_EFFECTS.sort(() => 0.5 - Math.random()).slice(0, Math.floor(Math.random() * 3) + 1),
        created_at: Date.now(),
      }));
      setSkills(prev => [...prev, ...batchSkills]);
      showMessage(`${count} skills simulated (offline)`, 'info');
    }
  };

  const handleComposeSkills = async () => {
    if (!selectedSkillId1 || !selectedSkillId2) { showMessage('Select two skills to compose', 'error'); return; }
    if (!composedSkillName.trim()) { showMessage('Composed skill name is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/compose-skills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: composedSkillName,
          skill_ids: [selectedSkillId1, selectedSkillId2],
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const composed: ComposedSkill = {
        id: data.id || uid(),
        name: data.name || composedSkillName,
        source_skills: data.source_skills || [selectedSkillId1, selectedSkillId2],
        combined_effects: data.combined_effects || [],
        power_level: data.power_level || 0,
        synergy_score: data.synergy_score || 0,
        created_at: data.created_at || Date.now(),
      };
      setComposedSkills(prev => [...prev, composed]);
      setComposedSkillName('');
      showMessage(`Composed skill "${composed.name}" created`, 'success');
    } catch {
      const skill1 = skills.find(s => s.id === selectedSkillId1);
      const skill2 = skills.find(s => s.id === selectedSkillId2);
      const composed: ComposedSkill = {
        id: uid(),
        name: composedSkillName,
        source_skills: [selectedSkillId1, selectedSkillId2],
        combined_effects: [
          ...new Set([...(skill1?.effects || []), ...(skill2?.effects || [])]),
        ],
        power_level: Math.floor(Math.random() * 100) + 50,
        synergy_score: Math.floor(Math.random() * 100),
        created_at: Date.now(),
      };
      setComposedSkills(prev => [...prev, composed]);
      setComposedSkillName('');
      showMessage(`Composed skill "${composedSkillName}" simulated (offline)`, 'info');
    }
  };

  const handleEvaluateSkill = async () => {
    if (!evaluateSkillId) { showMessage('Select a skill to evaluate', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/evaluate-skill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_id: evaluateSkillId }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const evaluation: EvaluationResult = {
        id: data.id || uid(),
        skill_name: data.skill_name || '',
        score: data.score || 0,
        balance_rating: data.balance_rating || 'balanced',
        metrics: data.metrics || {},
        feedback: data.feedback || '',
        evaluated_at: data.evaluated_at || Date.now(),
      };
      setLastEvaluation(evaluation);
      setEvaluations(prev => [...prev, evaluation]);
      showMessage(`Skill evaluated - Score: ${evaluation.score}/100 (${evaluation.balance_rating})`, 'success');
    } catch {
      const skill = skills.find(s => s.id === evaluateSkillId);
      const evaluation: EvaluationResult = {
        id: uid(),
        skill_name: skill?.name || 'unknown',
        score: Math.floor(Math.random() * 40) + 60,
        balance_rating: ['underpowered', 'balanced', 'overpowered'][Math.floor(Math.random() * 3)],
        metrics: Object.fromEntries(METRIC_KEYS.map(k => [k, Math.floor(Math.random() * 100)])),
        feedback: 'Simulated evaluation. Balance appears reasonable.',
        evaluated_at: Date.now(),
      };
      setLastEvaluation(evaluation);
      setEvaluations(prev => [...prev, evaluation]);
      showMessage('Skill evaluated (offline simulation)', 'info');
    }
  };

  const handleGenerateSkillTree = async () => {
    if (!treeName.trim()) { showMessage('Tree name is required', 'error'); return; }
    if (!treeRootSkill.trim()) { showMessage('Root skill is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/generate-skill-tree`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: treeName,
          root_skill: treeRootSkill,
          depth: parseInt(treeDepth) || 4,
          branches: parseInt(treeBranches) || 3,
        }),
      });
      const data = await res.json();
      if (data.error) { showMessage(data.error, 'error'); return; }
      const tree: SkillTreeItem = {
        id: data.id || uid(),
        name: data.name || treeName,
        root_skill: data.root_skill || treeRootSkill,
        nodes: data.nodes || [],
        created_at: data.created_at || Date.now(),
      };
      setSkillTrees(prev => [...prev, tree]);
      showMessage(`Skill tree "${tree.name}" generated with ${tree.nodes.length} nodes`, 'success');
    } catch {
      const generateNodes = (parentId: string | null, depth: number, branchIdx: number): SkillTreeNode[] => {
        if (depth <= 0) return [];
        const nodeId = uid();
        const node: SkillTreeNode = {
          id: nodeId,
          name: `${treeRootSkill}_branch${branchIdx}_depth${depth}`,
          parent_id: parentId,
          level_required: Math.max(1, parseInt(treeDepth) - depth + 1),
          unlocks: SKILL_EFFECTS.sort(() => 0.5 - Math.random()).slice(0, 2),
          children: [],
        };
        const childBranches = depth > 1 ? Math.min(2, parseInt(treeBranches)) : 0;
        const children: SkillTreeNode[] = [];
        for (let b = 0; b < childBranches; b++) {
          children.push(...generateNodes(nodeId, depth - 1, b));
        }
        node.children = children.map(c => c.id);
        return [node, ...children];
      };

      const nodes: SkillTreeNode[] = [];
      const rootNode: SkillTreeNode = {
        id: uid(),
        name: treeRootSkill,
        parent_id: null,
        level_required: 1,
        unlocks: ['damage', 'buff'],
        children: [],
      };
      nodes.push(rootNode);
      for (let b = 0; b < parseInt(treeBranches); b++) {
        const branchNodes = generateNodes(rootNode.id, parseInt(treeDepth) - 1, b);
        nodes.push(...branchNodes);
      }
      rootNode.children = nodes.filter(n => n.parent_id === rootNode.id).map(n => n.id);

      const tree: SkillTreeItem = {
        id: uid(),
        name: treeName,
        root_skill: treeRootSkill,
        nodes,
        created_at: Date.now(),
      };
      setSkillTrees(prev => [...prev, tree]);
      showMessage(`Skill tree "${treeName}" simulated (offline)`, 'info');
    }
  };

  const styles: Record<string, React.CSSProperties> = {
    container: { background: '#1a1a2e', color: '#e0e0e0', padding: 20, borderRadius: 8, fontFamily: 'monospace' },
    header: { fontSize: 18, fontWeight: 'bold', marginBottom: 16, color: '#e94560' },
    tabs: { display: 'flex', gap: 4, marginBottom: 16, flexWrap: 'wrap' },
    tab: { padding: '8px 16px', borderRadius: '6px 6px 0 0', border: 'none', cursor: 'pointer', fontSize: 13, background: '#2a2a4a', color: '#aab' },
    tabActive: { background: '#0f3460', color: '#e94560', fontWeight: 'bold' },
    card: { background: '#16213e', borderRadius: 8, padding: 16, marginBottom: 12 },
    cardTitle: { fontSize: 14, fontWeight: 'bold', color: '#e94560', marginBottom: 8 },
    input: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', boxSizing: 'border-box' as const },
    select: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13 },
    textarea: { background: '#1a1a3a', border: '1px solid #3a3a6a', color: '#e0e0e0', padding: '8px 12px', borderRadius: 6, fontSize: 13, width: '100%', resize: 'vertical' as const, minHeight: 60, boxSizing: 'border-box' as const, fontFamily: 'monospace' },
    btn: { background: '#e94560', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 'bold' },
    btnSecondary: { background: '#0f3460', color: '#aab', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 },
    row: { display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, flexWrap: 'wrap' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 },
    label: { fontSize: 12, color: '#889', marginBottom: 4 },
    value: { fontSize: 14, color: '#e0e0e0', fontWeight: 'bold' },
    badge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 'bold' },
    msgSuccess: { background: '#1a4a1a', color: '#4caf50', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgError: { background: '#4a1a1a', color: '#f44336', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    msgInfo: { background: '#1a2a4a', color: '#7c9aff', padding: '8px 16px', borderRadius: 6, marginBottom: 12 },
    treeContainer: { background: '#1a1a3a', borderRadius: 8, padding: 16, marginTop: 8 },
    treeNode: { padding: '6px 12px', borderRadius: 6, marginBottom: 4, fontSize: 12 },
    statBar: { height: 6, borderRadius: 3, background: '#2a2a4a', overflow: 'hidden', marginTop: 4 },
    statFill: { height: '100%', borderRadius: 3, background: '#e94560', transition: 'width 0.3s ease' },
    divider: { border: 'none', borderTop: '1px solid #2a2a4a', margin: '12px 0' },
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      combat: '#e94560', magic: '#7c3aed', defense: '#3b82f6', support: '#10b981',
      utility: '#f59e0b', movement: '#06b6d4', summon: '#ec4899', stealth: '#6b7280',
      healing: '#22c55e', elemental: '#f97316',
    };
    return colors[category] || '#607d8b';
  };

  const getBalanceColor = (rating: string) => {
    if (rating === 'balanced') return '#4caf50';
    if (rating === 'overpowered') return '#f44336';
    if (rating === 'underpowered') return '#ff9800';
    return '#607d8b';
  };

  const renderStats = () => (
    <div style={{ ...styles.card, background: '#16213e' }}>
      <div style={styles.cardTitle}>Skill Generator Statistics</div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
        <div style={{ textAlign: 'center', minWidth: 100 }}>
          <div style={styles.label}>Skills</div>
          <div style={{ ...styles.value, color: '#e94560' }}>{skills.length}</div>
        </div>
        <div style={{ textAlign: 'center', minWidth: 100 }}>
          <div style={styles.label}>Templates</div>
          <div style={{ ...styles.value, color: '#e94560' }}>{templates.length}</div>
        </div>
        <div style={{ textAlign: 'center', minWidth: 100 }}>
          <div style={styles.label}>Composed</div>
          <div style={{ ...styles.value, color: '#e94560' }}>{composedSkills.length}</div>
        </div>
        <div style={{ textAlign: 'center', minWidth: 100 }}>
          <div style={styles.label}>Skill Trees</div>
          <div style={{ ...styles.value, color: '#e94560' }}>{skillTrees.length}</div>
        </div>
        <div style={{ textAlign: 'center', minWidth: 100 }}>
          <div style={styles.label}>Evaluations</div>
          <div style={{ ...styles.value, color: '#e94560' }}>{evaluations.length}</div>
        </div>
      </div>
    </div>
  );

  const renderGenerateTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Generate Skill</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Skill name" value={skillName} onChange={e => setSkillName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <select style={styles.select} value={skillCategory} onChange={e => setSkillCategory(e.target.value)}>
            {SKILL_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <input style={{ ...styles.input, width: 100 }} placeholder="Level" value={skillLevel} onChange={e => setSkillLevel(e.target.value)} type="number" min="1" max="20" />
          <button style={styles.btn} onClick={handleGenerateSkill}>Generate Skill</button>
        </div>
        <div style={styles.row}>
          <textarea style={styles.textarea} placeholder="Optional prompt for AI generation..." value={skillPrompt} onChange={e => setSkillPrompt(e.target.value)} />
        </div>
      </div>

      {generatedSkill && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Generated: {generatedSkill.name}</div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 12 }}>
            <span style={{ ...styles.badge, background: getCategoryColor(generatedSkill.category) }}>{generatedSkill.category}</span>
            <span style={{ ...styles.badge, background: '#0f3460' }}>Lv.{generatedSkill.level}</span>
            <span style={{ ...styles.badge, background: '#2a3a1a' }}>DMG: {generatedSkill.damage}</span>
            <span style={{ ...styles.badge, background: '#3a2a1a' }}>CD: {generatedSkill.cooldown}s</span>
            <span style={{ ...styles.badge, background: '#2a1a4a' }}>MP: {generatedSkill.mana_cost}</span>
          </div>
          <div style={{ fontSize: 13, color: '#ccc', marginBottom: 8 }}>{generatedSkill.description}</div>
          {generatedSkill.effects.length > 0 && (
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {generatedSkill.effects.map(effect => (
                <span key={effect} style={{ ...styles.badge, background: '#1a2a3a', fontSize: 10 }}>{effect}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={styles.card}>
        <div style={styles.cardTitle}>Create Template</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Template name" value={templateName} onChange={e => setTemplateName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <select style={styles.select} value={templateCategory} onChange={e => setTemplateCategory(e.target.value)}>
            {SKILL_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <input style={{ ...styles.input, width: 100 }} placeholder="Base DMG" value={templateBaseDamage} onChange={e => setTemplateBaseDamage(e.target.value)} type="number" />
          <input style={{ ...styles.input, width: 100 }} placeholder="Base CD" value={templateBaseCooldown} onChange={e => setTemplateBaseCooldown(e.target.value)} type="number" />
          <button style={styles.btnSecondary} onClick={handleCreateTemplate}>Create Template</button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Batch Generate</div>
        <div style={styles.row}>
          <select style={styles.select} value={batchCategory} onChange={e => setBatchCategory(e.target.value)}>
            {SKILL_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <input style={{ ...styles.input, width: 100 }} placeholder="Count" value={batchCount} onChange={e => setBatchCount(e.target.value)} type="number" min="1" max="50" />
          <button style={styles.btn} onClick={handleBatchGenerate}>Batch Generate</button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Skill List ({skills.length})</div>
        {skills.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No skills generated yet. Create one above.</div>}
        <div style={styles.grid}>
          {skills.map(skill => (
            <div key={skill.id} style={{ ...styles.card, background: '#1a1a3a', borderLeft: `4px solid ${getCategoryColor(skill.category)}` }}>
              <div style={{ ...styles.cardTitle, fontSize: 13 }}>{skill.name}</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                <span style={{ ...styles.badge, background: getCategoryColor(skill.category), fontSize: 10 }}>{skill.category}</span>
                <span style={{ ...styles.badge, background: '#0f3460', fontSize: 10 }}>Lv.{skill.level}</span>
              </div>
              <div style={{ fontSize: 12, color: '#889' }}>
                <div>DMG: {skill.damage} | CD: {skill.cooldown}s | MP: {skill.mana_cost}</div>
                {skill.effects.length > 0 && (
                  <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap', marginTop: 4 }}>
                    {skill.effects.map(e => (
                      <span key={e} style={{ ...styles.badge, background: '#0f3460', fontSize: 9 }}>{e}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Template List ({templates.length})</div>
        {templates.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No templates created yet.</div>}
        <div style={styles.grid}>
          {templates.map(template => (
            <div key={template.id} style={{ ...styles.card, background: '#1a1a3a', borderLeft: `4px solid ${getCategoryColor(template.category)}` }}>
              <div style={{ ...styles.cardTitle, fontSize: 13 }}>{template.name}</div>
              <span style={{ ...styles.badge, background: getCategoryColor(template.category), fontSize: 10 }}>{template.category}</span>
              <div style={{ fontSize: 12, color: '#889', marginTop: 8 }}>
                {Object.entries(template.base_stats).map(([key, value]) => (
                  <div key={key}>{key}: {value}</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderComposeTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Compose Skills</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="New skill name" value={composedSkillName} onChange={e => setComposedSkillName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <select style={styles.select} value={selectedSkillId1} onChange={e => setSelectedSkillId1(e.target.value)}>
            <option value="">-- Skill 1 --</option>
            {skills.map(s => <option key={s.id} value={s.id}>{s.name} ({s.category})</option>)}
          </select>
          <select style={styles.select} value={selectedSkillId2} onChange={e => setSelectedSkillId2(e.target.value)}>
            <option value="">-- Skill 2 --</option>
            {skills.map(s => <option key={s.id} value={s.id}>{s.name} ({s.category})</option>)}
          </select>
          <button style={styles.btn} onClick={handleComposeSkills} disabled={!selectedSkillId1 || !selectedSkillId2}>Compose</button>
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.cardTitle}>Evaluate Skill</div>
        <div style={styles.row}>
          <select style={styles.select} value={evaluateSkillId} onChange={e => setEvaluateSkillId(e.target.value)}>
            <option value="">-- Select Skill --</option>
            {skills.map(s => <option key={s.id} value={s.id}>{s.name} ({s.category})</option>)}
          </select>
          <button style={styles.btn} onClick={handleEvaluateSkill} disabled={!evaluateSkillId}>Evaluate</button>
        </div>
      </div>

      {lastEvaluation && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Evaluation: {lastEvaluation.skill_name}</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12, alignItems: 'center' }}>
            <span style={{ fontSize: 24, fontWeight: 'bold', color: '#e94560' }}>{lastEvaluation.score}</span>
            <span style={{ fontSize: 13, color: '#889' }}>/ 100</span>
            <span style={{ ...styles.badge, background: getBalanceColor(lastEvaluation.balance_rating) }}>
              {lastEvaluation.balance_rating}
            </span>
          </div>
          <div style={{ fontSize: 13, color: '#ccc', marginBottom: 12 }}>{lastEvaluation.feedback}</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.entries(lastEvaluation.metrics).map(([key, value]) => (
              <div key={key}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                  <span style={{ color: '#889' }}>{key.replace(/_/g, ' ')}</span>
                  <span style={{ color: '#e0e0e0' }}>{Math.round(value)}</span>
                </div>
                <div style={styles.statBar}>
                  <div style={{ ...styles.statFill, width: `${Math.min(100, value)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {composedSkills.length > 0 && (
        <div style={styles.card}>
          <div style={styles.cardTitle}>Composed Skills ({composedSkills.length})</div>
          <div style={styles.grid}>
            {composedSkills.map(cs => (
              <div key={cs.id} style={{ ...styles.card, background: '#1a1a3a', borderLeft: '4px solid #e94560' }}>
                <div style={{ ...styles.cardTitle, fontSize: 13 }}>{cs.name}</div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                  <span style={{ ...styles.badge, background: '#0f3460', fontSize: 10 }}>Power: {cs.power_level}</span>
                  <span style={{ ...styles.badge, background: '#2a4a1a', fontSize: 10 }}>Synergy: {cs.synergy_score}%</span>
                </div>
                <div style={{ fontSize: 11, color: '#889', marginBottom: 6 }}>
                  Sources: {cs.source_skills.map(id => skills.find(s => s.id === id)?.name || id).join(' + ')}
                </div>
                {cs.combined_effects.length > 0 && (
                  <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                    {cs.combined_effects.map(e => (
                      <span key={e} style={{ ...styles.badge, background: '#3a2a5a', fontSize: 9 }}>{e}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={styles.card}>
        <div style={styles.cardTitle}>Evaluation History ({evaluations.length})</div>
        {evaluations.length === 0 && <div style={{ color: '#889', fontSize: 13 }}>No evaluations yet.</div>}
        {evaluations.map(ev => (
          <div key={ev.id} style={{ ...styles.card, background: '#1a1a3a', marginBottom: 8, borderLeft: `4px solid ${getBalanceColor(ev.balance_rating)}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div style={{ fontSize: 13, fontWeight: 'bold', color: '#e0e0e0' }}>{ev.skill_name}</div>
              <span style={{ ...styles.badge, background: getBalanceColor(ev.balance_rating), fontSize: 10 }}>{ev.balance_rating}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 18, fontWeight: 'bold', color: '#e94560' }}>{ev.score}</span>
              <span style={{ fontSize: 11, color: '#889' }}>/100</span>
            </div>
            <div style={{ fontSize: 11, color: '#889', marginTop: 4 }}>{ev.feedback}</div>
          </div>
        ))}
      </div>
    </div>
  );

  const renderSkillTree = (tree: SkillTreeItem, baseIndent = 0) => {
    const rootNode = tree.nodes.find(n => n.parent_id === null);
    if (!rootNode) return null;

    const renderNode = (node: SkillTreeNode, depth: number): React.ReactNode => {
      const children = tree.nodes.filter(n => node.children.includes(n.id));
      return (
        <div key={node.id} style={{ marginLeft: depth * 20 }}>
          <div style={{
            ...styles.treeNode,
            background: depth === 0 ? '#0f3460' : '#1a1a3a',
            borderLeft: `3px solid ${getCategoryColor(SKILL_CATEGORIES[depth % SKILL_CATEGORIES.length])}`,
            marginTop: depth > 0 ? 4 : 0,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: depth === 0 ? 'bold' : 'normal', color: depth === 0 ? '#e94560' : '#e0e0e0', fontSize: depth === 0 ? 13 : 12 }}>
                {depth === 0 ? '⭐ ' : depth === 1 ? '▶ ' : '• '}{node.name}
              </span>
              <span style={{ ...styles.badge, background: '#0f3460', fontSize: 9 }}>
                Lv.{node.level_required}
              </span>
            </div>
            {node.unlocks.length > 0 && (
              <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap', marginTop: 4 }}>
                {node.unlocks.map(u => (
                  <span key={u} style={{ ...styles.badge, background: '#2a3a5a', fontSize: 9 }}>{u}</span>
                ))}
              </div>
            )}
          </div>
          {children.map(child => renderNode(child, depth + 1))}
        </div>
      );
    };

    return renderNode(rootNode, 0);
  };

  const renderTreesTab = () => (
    <div>
      <div style={styles.card}>
        <div style={styles.cardTitle}>Generate Skill Tree</div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Tree name" value={treeName} onChange={e => setTreeName(e.target.value)} />
        </div>
        <div style={styles.row}>
          <input style={styles.input} placeholder="Root skill name" value={treeRootSkill} onChange={e => setTreeRootSkill(e.target.value)} />
        </div>
        <div style={styles.row}>
          <input style={{ ...styles.input, width: 100 }} placeholder="Depth" value={treeDepth} onChange={e => setTreeDepth(e.target.value)} type="number" min="2" max="10" />
          <input style={{ ...styles.input, width: 100 }} placeholder="Branches" value={treeBranches} onChange={e => setTreeBranches(e.target.value)} type="number" min="1" max="8" />
          <button style={styles.btn} onClick={handleGenerateSkillTree}>Generate Tree</button>
        </div>
      </div>

      {skillTrees.length === 0 && (
        <div style={{ color: '#889', fontSize: 13, marginBottom: 12 }}>No skill trees generated yet. Create one above.</div>
      )}

      {skillTrees.map(tree => (
        <div key={tree.id} style={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={styles.cardTitle}>{tree.name}</div>
            <div style={{ display: 'flex', gap: 6 }}>
              <span style={{ ...styles.badge, background: '#0f3460', fontSize: 10 }}>Root: {tree.root_skill}</span>
              <span style={{ ...styles.badge, background: '#2a3a5a', fontSize: 10 }}>{tree.nodes.length} nodes</span>
            </div>
          </div>
          <div style={styles.treeContainer}>
            {renderSkillTree(tree)}
          </div>
          <hr style={styles.divider} />
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {tree.nodes.map(node => (
              <span key={node.id} style={{ ...styles.badge, background: '#0f3460', fontSize: 9 }}>
                {node.name} (Lv.{node.level_required})
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  const TAB_CONFIG: { id: TabId; label: string; icon: string }[] = [
    { id: 'generate', label: 'Generate', icon: '⚡' },
    { id: 'compose', label: 'Compose', icon: '🔗' },
    { id: 'trees', label: 'Trees', icon: '🌳' },
  ];

  const renderTabContent = (tabId: TabId) => {
    switch (tabId) {
      case 'generate': return renderGenerateTab();
      case 'compose': return renderComposeTab();
      case 'trees': return renderTreesTab();
      default: return null;
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>⚡ AI Skill Generator</div>
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

export default SkillGeneratorPanel;