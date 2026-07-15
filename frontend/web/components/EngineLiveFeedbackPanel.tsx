"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

const CATEGORIES = ['performance', 'balance', 'visual', 'audio', 'ui_ux', 'gameplay', 'accessibility', 'localization', 'networking', 'security'];
const SEVERITIES = ['low', 'medium', 'high', 'critical'];
const SCOPES = ['entity', 'scene', 'project', 'runtime'];

interface FeedbackStats {
  total_analyses: number;
  total_feedback_items: number;
  fixes_applied: number;
  feedback_by_category: Record<string, number>;
}

interface FeedbackItem {
  id: string;
  entity_id: string;
  category: string;
  severity: string;
  scope: string;
  title: string;
  description: string;
  suggestion: string;
  fixed: boolean;
  created_at: number;
}

interface AnalysisResult {
  id: string;
  entity_id: string;
  type: string;
  issues_found: number;
  score: number;
  summary: string;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineLiveFeedbackPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<FeedbackStats>({ total_analyses: 0, total_feedback_items: 0, fixes_applied: 0, feedback_by_category: {} });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);

  // Analyze form state
  const [entityId, setEntityId] = useState('');
  const [entityData, setEntityData] = useState('');
  const [sceneData, setSceneData] = useState('');
  const [projectData, setProjectData] = useState('');
  const [runtimeData, setRuntimeData] = useState('');

  // Filter state
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [filterScope, setFilterScope] = useState('all');

  // Fix form state
  const [fixFeedbackId, setFixFeedbackId] = useState('');

  // Analysis result
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/live-feedback/stats`);
      if (r.ok) {
        const data = await r.json();
        setStats(data.stats || data);
      }
    } catch (e) { console.error(e); }
  }, []);

  const fetchFeedback = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filterCategory !== 'all') params.set('category', filterCategory);
      if (filterSeverity !== 'all') params.set('severity', filterSeverity);
      if (filterScope !== 'all') params.set('scope', filterScope);
      const r = await fetch(`${API_BASE}/live-feedback/feedback?${params}`);
      if (r.ok) setFeedback(await r.json());
    } catch (e) { console.error(e); }
  }, [filterCategory, filterSeverity, filterScope]);

  useEffect(() => {
    fetchStats();
    fetchFeedback();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchFeedback]);

  const handleSubmit = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setMessage(r.ok ? 'Success' : data.detail || data.message || 'Failed');
      fetchStats();
      fetchFeedback();
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const analyzeEntity = async () => {
    try {
      const parsed = entityData ? JSON.parse(entityData) : {};
      const result = await handleSubmit(`${API_BASE}/live-feedback/analyze-entity`, { entity_id: entityId, entity_data: parsed });
      if (result) setAnalysisResult(result.analysis || result);
      setEntityId('');
      setEntityData('');
    } catch { setMessage('Invalid JSON in entity data'); }
  };

  const analyzeScene = async () => {
    try {
      const parsed = sceneData ? JSON.parse(sceneData) : {};
      const result = await handleSubmit(`${API_BASE}/live-feedback/analyze-scene`, { scene_data: parsed });
      if (result) setAnalysisResult(result.analysis || result);
      setSceneData('');
    } catch { setMessage('Invalid JSON in scene data'); }
  };

  const analyzeProject = async () => {
    try {
      const parsed = projectData ? JSON.parse(projectData) : {};
      const result = await handleSubmit(`${API_BASE}/live-feedback/analyze-project`, { project_data: parsed });
      if (result) setAnalysisResult(result.analysis || result);
      setProjectData('');
    } catch { setMessage('Invalid JSON in project data'); }
  };

  const analyzeRuntime = async () => {
    try {
      const parsed = runtimeData ? JSON.parse(runtimeData) : {};
      const result = await handleSubmit(`${API_BASE}/live-feedback/analyze-runtime`, { runtime_data: parsed });
      if (result) setAnalysisResult(result.analysis || result);
      setRuntimeData('');
    } catch { setMessage('Invalid JSON in runtime data'); }
  };

  const applyFix = async () => {
    await handleSubmit(`${API_BASE}/live-feedback/apply-fix`, { feedback_id: fixFeedbackId });
    setFixFeedbackId('');
  };

  const tabs = ['overview', 'analyze', 'results', 'fixes'];

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#ff6b6b';
      case 'high': return '#ff9f43';
      case 'medium': return '#fdcb6e';
      case 'low': return '#6bcb77';
      default: return '#6bcb77';
    }
  };

  const getCategoryBadgeColor = (category: string) => {
    const colors: Record<string, string> = {
      performance: 'bg-red-900/50 text-red-300',
      balance: 'bg-yellow-900/50 text-yellow-300',
      visual: 'bg-purple-900/50 text-purple-300',
      audio: 'bg-indigo-900/50 text-indigo-300',
      ui_ux: 'bg-blue-900/50 text-blue-300',
      gameplay: 'bg-green-900/50 text-green-300',
      accessibility: 'bg-teal-900/50 text-teal-300',
      localization: 'bg-cyan-900/50 text-cyan-300',
      networking: 'bg-orange-900/50 text-orange-300',
      security: 'bg-pink-900/50 text-pink-300',
    };
    return colors[category] || 'bg-[#1a1a1a]/50 text-[#ccc]';
  };

  const overviewContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Live Feedback Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Analyses', value: stats.total_analyses, color: '#00d4ff' },
          { label: 'Feedback Items', value: stats.total_feedback_items, color: '#fdcb6e' },
          { label: 'Fixes Applied', value: stats.fixes_applied, color: '#6bcb77' },
          { label: 'Open Issues', value: stats.total_feedback_items - stats.fixes_applied, color: '#ff6b6b' },
        ].map(s => (
          <div key={s.label} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-[#999] mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {Object.keys(stats.feedback_by_category).length > 0 && (
        <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Feedback by Category</h3>
          <div className="space-y-2">
            {Object.entries(stats.feedback_by_category).map(([category, count]) => (
              <div key={category} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs ${getCategoryBadgeColor(category)} capitalize`}>{category.replace(/_/g, ' ')}</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-32 h-2 bg-[#1a1a2e] rounded-full overflow-hidden">
                    <div className="h-full bg-[#00d4ff] rounded-full" style={{ width: `${Math.min(100, (count / Math.max(stats.total_feedback_items, 1)) * 100)}%` }} />
                  </div>
                  <span className="text-xs text-[#999] w-8 text-right">{count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const analyzeContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Run Analysis</h2>

      {/* Entity Analysis */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Entity Analysis</h3>
        <div className="grid grid-cols-1 gap-3 mb-3">
          <input
            type="text" placeholder="Entity ID"
            value={entityId}
            onChange={e => setEntityId(e.target.value)}
            className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <textarea
            placeholder='Entity Data (JSON) e.g. {"type": "player", "position": {...}}'
            value={entityData}
            onChange={e => setEntityData(e.target.value)}
            rows={3}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none resize-none font-mono"
          />
        </div>
        <button
          onClick={analyzeEntity} disabled={loading || !entityId}
          className="bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors"
        >
          Analyze Entity
        </button>
      </div>

      {/* Scene Analysis */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Scene Analysis</h3>
        <div className="mb-3">
          <textarea
            placeholder='Scene Data (JSON) e.g. {"name": "Level1", "objects": [...]}'
            value={sceneData}
            onChange={e => setSceneData(e.target.value)}
            rows={3}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none resize-none font-mono"
          />
        </div>
        <button
          onClick={analyzeScene} disabled={loading || !sceneData}
          className="bg-[#6bcb77] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#5ab867] disabled:opacity-50 transition-colors"
        >
          Analyze Scene
        </button>
      </div>

      {/* Project Analysis */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Project Analysis</h3>
        <div className="mb-3">
          <textarea
            placeholder='Project Data (JSON) e.g. {"name": "MyGame", "settings": {...}}'
            value={projectData}
            onChange={e => setProjectData(e.target.value)}
            rows={3}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none resize-none font-mono"
          />
        </div>
        <button
          onClick={analyzeProject} disabled={loading || !projectData}
          className="bg-[#fdcb6e] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e8b94e] disabled:opacity-50 transition-colors"
        >
          Analyze Project
        </button>
      </div>

      {/* Runtime Analysis */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Runtime Analysis</h3>
        <div className="mb-3">
          <textarea
            placeholder='Runtime Data (JSON) e.g. {"fps": 60, "memory": 512}'
            value={runtimeData}
            onChange={e => setRuntimeData(e.target.value)}
            rows={3}
            className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none resize-none font-mono"
          />
        </div>
        <button
          onClick={analyzeRuntime} disabled={loading || !runtimeData}
          className="bg-[#ff9f43] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e88935] disabled:opacity-50 transition-colors"
        >
          Analyze Runtime
        </button>
      </div>

      {/* Analysis Result */}
      {analysisResult && (
        <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mt-4">
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Analysis Result</h3>
          <div className="flex gap-4 mb-3">
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-center">
              <div className="text-sm font-bold text-[#00d4ff]">{analysisResult.issues_found}</div>
              <div className="text-xs text-[#666]">Issues Found</div>
            </div>
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-center">
              <div className="text-sm font-bold" style={{ color: analysisResult.score >= 7 ? '#6bcb77' : analysisResult.score >= 4 ? '#fdcb6e' : '#ff6b6b' }}>{analysisResult.score}/10</div>
              <div className="text-xs text-[#666]">Score</div>
            </div>
          </div>
          {analysisResult.summary && (
            <p className="text-xs text-[#ccc]">{analysisResult.summary}</p>
          )}
        </div>
      )}
    </div>
  );

  const resultsContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Feedback Results</h2>

      {/* Filters */}
      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-[#666] block mb-1">Category</label>
            <select
              value={filterCategory}
              onChange={e => setFilterCategory(e.target.value)}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
            >
              <option value="all" className="bg-[#1a1a2e]">All Categories</option>
              {CATEGORIES.map(c => (
                <option key={c} value={c} className="bg-[#1a1a2e] capitalize">{c.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#666] block mb-1">Severity</label>
            <select
              value={filterSeverity}
              onChange={e => setFilterSeverity(e.target.value)}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
            >
              <option value="all" className="bg-[#1a1a2e]">All Severities</option>
              {SEVERITIES.map(s => (
                <option key={s} value={s} className="bg-[#1a1a2e] capitalize">{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#666] block mb-1">Scope</label>
            <select
              value={filterScope}
              onChange={e => setFilterScope(e.target.value)}
              className="w-full bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none"
            >
              <option value="all" className="bg-[#1a1a2e]">All Scopes</option>
              {SCOPES.map(s => (
                <option key={s} value={s} className="bg-[#1a1a2e] capitalize">{s}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Feedback List */}
      <div className="space-y-3">
        {feedback.map(item => (
          <div key={item.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-white">{item.title}</span>
                {item.fixed && (
                  <span className="px-2 py-0.5 bg-green-900/50 text-green-300 rounded text-xs">Fixed</span>
                )}
              </div>
              <span
                className="px-2 py-0.5 rounded text-xs font-medium"
                style={{ backgroundColor: getSeverityColor(item.severity) + '20', color: getSeverityColor(item.severity) }}
              >
                {item.severity.toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-[#999] mb-2">{item.description}</p>
            <div className="flex flex-wrap gap-2 mb-2">
              <span className={`px-2 py-0.5 rounded text-xs ${getCategoryBadgeColor(item.category)} capitalize`}>{item.category.replace(/_/g, ' ')}</span>
              <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc] capitalize">{item.scope}</span>
              <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#666]">{item.entity_id}</span>
            </div>
            {item.suggestion && (
              <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2">
                <span className="text-xs text-[#6bcb77]">Suggestion: </span>
                <span className="text-xs text-[#ccc]">{item.suggestion}</span>
              </div>
            )}
          </div>
        ))}
      </div>
      {feedback.length === 0 && (
        <div className="text-center text-[#666] py-8">No feedback items found. Run an analysis first.</div>
      )}
    </div>
  );

  const fixesContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Apply Fixes</h2>

      <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Apply Fix by Feedback ID</h3>
        <div className="flex gap-3 items-end">
          <input
            type="text" placeholder="Feedback ID"
            value={fixFeedbackId}
            onChange={e => setFixFeedbackId(e.target.value)}
            className="flex-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none"
          />
          <button
            onClick={applyFix} disabled={loading || !fixFeedbackId}
            className="bg-[#6bcb77] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#5ab867] disabled:opacity-50 transition-colors"
          >
            Apply Fix
          </button>
        </div>
      </div>

      {/* Unfixed Items Quick Reference */}
      {feedback.filter(f => !f.fixed).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Unfixed Items ({feedback.filter(f => !f.fixed).length})</h3>
          <div className="space-y-2">
            {feedback.filter(f => !f.fixed).map(item => (
              <div key={item.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3 flex items-center justify-between">
                <div>
                  <span className="text-sm text-white">{item.title}</span>
                  <span className="text-xs text-[#666] ml-2">ID: {item.id}</span>
                </div>
                <span
                  className="px-2 py-0.5 rounded text-xs font-medium"
                  style={{ backgroundColor: getSeverityColor(item.severity) + '20', color: getSeverityColor(item.severity) }}
                >
                  {item.severity}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a]">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && <div className="mx-4 mt-2 p-2 bg-[#0f0f23] border border-[#2a2a4a] rounded text-sm text-[#00d4ff]">{message}</div>}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && overviewContent}
        {activeTab === 'analyze' && analyzeContent}
        {activeTab === 'results' && resultsContent}
        {activeTab === 'fixes' && fixesContent}
      </div>
    </div>
  );
}