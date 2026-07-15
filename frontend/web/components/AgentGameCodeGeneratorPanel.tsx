"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT;

interface GeneratorStats {
  total_templates: number;
  total_generated: number;
  by_language: Record<string, number>;
  by_domain: Record<string, number>;
  by_status: Record<string, number>;
  [key: string]: any;
}

interface Template {
  id: string;
  name: string;
  language: string;
  domain: string;
  description: string;
  template_code?: string;
  parameters?: string[];
}

interface GeneratedCode {
  id: string;
  name: string;
  language: string;
  domain: string;
  status: string;
  description?: string;
  code?: string;
  metadata?: any;
  dependencies?: string[];
}

interface ReviewResult {
  quality_score: number;
  reviewer_comments: string[];
  issues_found: string[];
  suggestions: string[];
}

interface BundleInfo {
  bundle_id: string;
  bundle_name: string;
  entry_point: string;
  code_count: number;
  [key: string]: any;
}

const LANGUAGES = ['python', 'javascript', 'typescript', 'lua', 'csharp', 'cpp', 'go', 'rust', 'gdscript'];
const DOMAINS = ['gameplay', 'ai', 'physics', 'rendering', 'networking', 'audio', 'ui', 'systems', 'tools', 'shaders'];
const MODES = ['template', 'procedural', 'hybrid'];

type TabId = 'status' | 'templates' | 'generate' | 'review' | 'bundle' | 'generated';

const AgentGameCodeGeneratorPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('status');
  const [data, setData] = useState<GeneratorStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Templates tab
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templateFilterDomain, setTemplateFilterDomain] = useState('');
  const [templateFilterLanguage, setTemplateFilterLanguage] = useState('');
  const [newTemplateName, setNewTemplateName] = useState('');
  const [newTemplateLanguage, setNewTemplateLanguage] = useState('python');
  const [newTemplateDomain, setNewTemplateDomain] = useState('gameplay');
  const [newTemplateCode, setNewTemplateCode] = useState('');
  const [newTemplateParams, setNewTemplateParams] = useState('');
  const [newTemplateDesc, setNewTemplateDesc] = useState('');

  // Generate tab
  const [genDescription, setGenDescription] = useState('');
  const [genLanguage, setGenLanguage] = useState('python');
  const [genDomain, setGenDomain] = useState('gameplay');
  const [genMode, setGenMode] = useState('template');
  const [genResult, setGenResult] = useState<GeneratedCode | null>(null);

  // Review tab
  const [reviewCodeId, setReviewCodeId] = useState('');
  const [reviewCriteria, setReviewCriteria] = useState('');
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);

  // Bundle tab
  const [bundleName, setBundleName] = useState('');
  const [bundleEntryPoint, setBundleEntryPoint] = useState('');
  const [selectedCodeIds, setSelectedCodeIds] = useState<string[]>([]);
  const [bundleResult, setBundleResult] = useState<BundleInfo | null>(null);

  // Generated tab
  const [generatedCodes, setGeneratedCodes] = useState<GeneratedCode[]>([]);
  const [genFilterDomain, setGenFilterDomain] = useState('');
  const [genFilterLanguage, setGenFilterLanguage] = useState('');
  const [viewCodeId, setViewCodeId] = useState<string | null>(null);
  const [viewCodeDetail, setViewCodeDetail] = useState<GeneratedCode | null>(null);

  const tabs = [
    { id: 'status' as TabId, label: 'Status' },
    { id: 'templates' as TabId, label: 'Templates' },
    { id: 'generate' as TabId, label: 'Generate' },
    { id: 'review' as TabId, label: 'Review' },
    { id: 'bundle' as TabId, label: 'Bundle' },
    { id: 'generated' as TabId, label: 'Generated' },
  ];

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/game-code-generator/stats`);
      if (res.ok) setData(await res.json());
    } catch (e) {
      console.error(e);
    }
  }, []);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/game-code-generator/templates`);
      if (res.ok) {
        const json = await res.json();
        setTemplates(json.templates || json || []);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  const fetchGenerated = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/game-code-generator/generated`);
      if (res.ok) {
        const json = await res.json();
        setGeneratedCodes(json.codes || json.generated || json || []);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchTemplates();
    fetchGenerated();
    const i = setInterval(fetchStats, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchTemplates, fetchGenerated]);

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleSubmit = async (endpoint: string, body: any) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const result = await res.json();
        showMessage('success', 'Operation successful');
        setLoading(false);
        return result;
      } else {
        showMessage('error', `Error: ${res.status}`);
        setLoading(false);
        return null;
      }
    } catch (e: any) {
      showMessage('error', e.message);
      setLoading(false);
      return null;
    }
  };

  const filteredTemplates = templates.filter((t) => {
    if (templateFilterDomain && t.domain !== templateFilterDomain) return false;
    if (templateFilterLanguage && t.language !== templateFilterLanguage) return false;
    return true;
  });

  const filteredGenerated = generatedCodes.filter((g) => {
    if (genFilterDomain && g.domain !== genFilterDomain) return false;
    if (genFilterLanguage && g.language !== genFilterLanguage) return false;
    return true;
  });

  const renderStatusTab = () => (
    <div>
      {data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">Total Templates</span>
              <div className="text-white text-2xl font-bold mt-1">{data.total_templates}</div>
            </div>
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <span className="text-[#999] text-xs">Total Generated</span>
              <div className="text-white text-2xl font-bold mt-1">{data.total_generated}</div>
            </div>
          </div>

          {data.by_language && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-[#00d4ff] mb-3">By Language</div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(data.by_language).map(([lang, count]) => (
                  <div key={lang} className="flex justify-between items-center bg-[#0f0f23] rounded px-3 py-2">
                    <span className="text-[#ccc] text-xs capitalize">{lang}</span>
                    <span className="text-white text-xs font-mono">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.by_domain && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-[#00d4ff] mb-3">By Domain</div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(data.by_domain).map(([domain, count]) => (
                  <div key={domain} className="flex justify-between items-center bg-[#0f0f23] rounded px-3 py-2">
                    <span className="text-[#ccc] text-xs capitalize">{domain}</span>
                    <span className="text-white text-xs font-mono">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.by_status && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-[#00d4ff] mb-3">By Status</div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(data.by_status).map(([status, count]) => (
                  <div key={status} className="flex justify-between items-center bg-[#0f0f23] rounded px-3 py-2">
                    <span className="text-[#ccc] text-xs capitalize">{status}</span>
                    <span className="text-white text-xs font-mono">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-[#999] text-sm">No code generator stats available</div>
      )}
    </div>
  );

  const renderTemplatesTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Create Template</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Name</label>
            <input type="text" value={newTemplateName} onChange={(e) => setNewTemplateName(e.target.value)} placeholder="player_controller" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Language</label>
            <select value={newTemplateLanguage} onChange={(e) => setNewTemplateLanguage(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Domain</label>
            <select value={newTemplateDomain} onChange={(e) => setNewTemplateDomain(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Parameters (comma-separated)</label>
            <input type="text" value={newTemplateParams} onChange={(e) => setNewTemplateParams(e.target.value)} placeholder="speed, jump_height, gravity" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Template Code</label>
            <textarea value={newTemplateCode} onChange={(e) => setNewTemplateCode(e.target.value)} placeholder="def {{name}}({{params}}):&#10;    pass" rows={5} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm font-mono focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Description</label>
            <textarea value={newTemplateDesc} onChange={(e) => setNewTemplateDesc(e.target.value)} placeholder="A reusable player controller template..." rows={2} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!newTemplateName.trim()) { showMessage('error', 'Template name required'); return; }
            await handleSubmit('/agent/game-code-generator/create-template', {
              name: newTemplateName,
              language: newTemplateLanguage,
              domain: newTemplateDomain,
              template_code: newTemplateCode,
              parameters: newTemplateParams ? newTemplateParams.split(',').map((s) => s.trim()).filter(Boolean) : [],
              description: newTemplateDesc,
            });
            setNewTemplateName('');
            setNewTemplateCode('');
            setNewTemplateParams('');
            setNewTemplateDesc('');
            fetchTemplates();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Create Template
        </button>
      </div>

      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-medium text-[#00d4ff]">Templates ({filteredTemplates.length})</div>
          <div className="flex gap-2">
            <select value={templateFilterDomain} onChange={(e) => setTemplateFilterDomain(e.target.value)} className="bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs">
              <option value="">All Domains</option>
              {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <select value={templateFilterLanguage} onChange={(e) => setTemplateFilterLanguage(e.target.value)} className="bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs">
              <option value="">All Languages</option>
              {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
        </div>
        {filteredTemplates.length > 0 ? (
          <div className="space-y-2">
            {filteredTemplates.map((t) => (
              <div key={t.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-white text-sm font-medium">{t.name}</span>
                  <div className="flex gap-1">
                    <span className="text-xs bg-[#1a1a2e] text-[#00d4ff] px-2 py-0.5 rounded">{t.language}</span>
                    <span className="text-xs bg-[#1a1a2e] text-[#ccc] px-2 py-0.5 rounded">{t.domain}</span>
                  </div>
                </div>
                {t.description && <div className="text-[#999] text-xs mt-1">{t.description}</div>}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No templates found</div>
        )}
      </div>
    </div>
  );

  const renderGenerateTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Generate Code</div>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Description</label>
            <textarea value={genDescription} onChange={(e) => setGenDescription(e.target.value)} placeholder="Describe the code you want to generate...&#10;e.g., A 2D platformer player controller with double jump and wall slide" rows={4} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target Language</label>
            <select value={genLanguage} onChange={(e) => setGenLanguage(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Target Domain</label>
            <select value={genDomain} onChange={(e) => setGenDomain(e.target.value)} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none">
              {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Generation Mode</label>
            <div className="flex gap-2">
              {MODES.map((m) => (
                <button
                  key={m}
                  onClick={() => setGenMode(m)}
                  className={`px-4 py-2 rounded text-sm font-medium ${genMode === m ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] border border-[#2a2a4a]'}`}
                >
                  {m.charAt(0).toUpperCase() + m.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
        <button
          onClick={async () => {
            if (!genDescription.trim()) { showMessage('error', 'Description required'); return; }
            const result = await handleSubmit('/agent/game-code-generator/generate', {
              description: genDescription,
              target_language: genLanguage,
              target_domain: genDomain,
              mode: genMode,
            });
            if (result) setGenResult(result);
            fetchStats();
            fetchGenerated();
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Generate Code
        </button>
      </div>

      {genResult && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-3">Generated Result</div>
          <div className="grid grid-cols-2 gap-2 mb-3">
            <div className="bg-[#0f0f23] rounded px-3 py-2">
              <span className="text-[#999] text-xs">Language</span>
              <div className="text-white text-xs mt-0.5 capitalize">{genResult.language || genLanguage}</div>
            </div>
            <div className="bg-[#0f0f23] rounded px-3 py-2">
              <span className="text-[#999] text-xs">Domain</span>
              <div className="text-white text-xs mt-0.5 capitalize">{genResult.domain || genDomain}</div>
            </div>
            <div className="bg-[#0f0f23] rounded px-3 py-2">
              <span className="text-[#999] text-xs">Status</span>
              <div className="text-white text-xs mt-0.5 capitalize">{genResult.status || 'generated'}</div>
            </div>
            {genResult.metadata && (
              <div className="bg-[#0f0f23] rounded px-3 py-2">
                <span className="text-[#999] text-xs">Metadata</span>
                <div className="text-white text-xs mt-0.5 font-mono">{JSON.stringify(genResult.metadata)}</div>
              </div>
            )}
          </div>
          {genResult.dependencies && genResult.dependencies.length > 0 && (
            <div className="mb-3">
              <span className="text-xs text-[#999]">Dependencies: </span>
              {genResult.dependencies.map((d: string, i: number) => (
                <span key={i} className="text-xs bg-[#0f0f23] text-[#00d4ff] px-2 py-0.5 rounded mr-1">{d}</span>
              ))}
            </div>
          )}
          <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg overflow-hidden">
            <div className="flex overflow-x-auto">
              <pre className="text-green-400 text-xs font-mono p-4 whitespace-pre-wrap w-full">
                {(genResult.code || genResult.name || '// Generated code will appear here')
                  .split('\n')
                  .map((line: string, i: number) => (
                    <div key={i} className="flex">
                      <span className="text-[#555] w-8 text-right mr-4 select-none flex-shrink-0">{i + 1}</span>
                      <span>{line}</span>
                    </div>
                  ))}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderReviewTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Review Code</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Code ID</label>
            <input type="text" value={reviewCodeId} onChange={(e) => setReviewCodeId(e.target.value)} placeholder="gen_abc123" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div></div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Review Criteria (optional)</label>
            <textarea value={reviewCriteria} onChange={(e) => setReviewCriteria(e.target.value)} placeholder="Check for: performance issues, security vulnerabilities, code style, edge cases..." rows={3} className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
        </div>
        <button
          onClick={async () => {
            if (!reviewCodeId.trim()) { showMessage('error', 'Code ID required'); return; }
            const result = await handleSubmit('/agent/game-code-generator/review', {
              code_id: reviewCodeId,
              criteria: reviewCriteria,
            });
            if (result) setReviewResult(result);
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Review Code
        </button>
      </div>

      {reviewResult && (
        <div className="space-y-3">
          <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
            <div className="text-sm font-medium text-[#00d4ff] mb-3">Quality Score</div>
            <div className="flex items-center gap-3">
              <div className="text-3xl font-bold text-white">{reviewResult.quality_score}</div>
              <div className="text-[#999] text-sm">/ 100</div>
              <div className="flex-1 bg-[#0f0f23] rounded-full h-2">
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${Math.min(100, reviewResult.quality_score)}%`,
                    backgroundColor: reviewResult.quality_score >= 80 ? '#4ade80' : reviewResult.quality_score >= 60 ? '#f59e0b' : '#ef4444',
                  }}
                />
              </div>
            </div>
          </div>

          {reviewResult.reviewer_comments && reviewResult.reviewer_comments.length > 0 && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-[#ccc] mb-2">Comments</div>
              {reviewResult.reviewer_comments.map((c: string, i: number) => (
                <div key={i} className="text-[#999] text-xs bg-[#0f0f23] rounded px-3 py-2 mb-1">{c}</div>
              ))}
            </div>
          )}

          {reviewResult.issues_found && reviewResult.issues_found.length > 0 && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-red-400 mb-2">Issues Found ({reviewResult.issues_found.length})</div>
              {reviewResult.issues_found.map((issue: string, i: number) => (
                <div key={i} className="text-red-300 text-xs bg-[#0f0f23] rounded px-3 py-2 mb-1 border-l-2 border-red-500">{issue}</div>
              ))}
            </div>
          )}

          {reviewResult.suggestions && reviewResult.suggestions.length > 0 && (
            <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
              <div className="text-sm font-medium text-green-400 mb-2">Suggestions</div>
              {reviewResult.suggestions.map((s: string, i: number) => (
                <div key={i} className="text-green-300 text-xs bg-[#0f0f23] rounded px-3 py-2 mb-1 border-l-2 border-green-500">{s}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );

  const renderBundleTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="text-sm font-medium text-[#00d4ff] mb-3">Bundle Codes</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-[#999] mb-1 block">Bundle Name</label>
            <input type="text" value={bundleName} onChange={(e) => setBundleName(e.target.value)} placeholder="my_game_bundle" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div>
            <label className="text-xs text-[#999] mb-1 block">Entry Point</label>
            <input type="text" value={bundleEntryPoint} onChange={(e) => setBundleEntryPoint(e.target.value)} placeholder="main.py" className="w-full bg-[#0f0f23] border border-[#2a2a4a] rounded px-3 py-2 text-white text-sm focus:border-[#00d4ff] focus:outline-none" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[#999] mb-1 block">Select Codes to Bundle</label>
            <div className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-2 max-h-48 overflow-auto">
              {generatedCodes.length > 0 ? generatedCodes.map((g) => (
                <label key={g.id} className="flex items-center gap-2 px-2 py-1.5 hover:bg-[#1a1a2e] rounded cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedCodeIds.includes(g.id)}
                    onChange={() => {
                      setSelectedCodeIds((prev) =>
                        prev.includes(g.id) ? prev.filter((id) => id !== g.id) : [...prev, g.id]
                      );
                    }}
                    className="accent-[#00d4ff]"
                  />
                  <span className="text-white text-xs">{g.name || g.id}</span>
                  <span className="text-[#666] text-xs">{g.language}</span>
                </label>
              )) : (
                <div className="text-[#666] text-xs px-2 py-1">No generated codes available. Generate some first.</div>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={async () => {
            if (!bundleName.trim()) { showMessage('error', 'Bundle name required'); return; }
            if (selectedCodeIds.length === 0) { showMessage('error', 'Select at least one code'); return; }
            const result = await handleSubmit('/agent/game-code-generator/bundle', {
              code_ids: selectedCodeIds,
              bundle_name: bundleName,
              entry_point: bundleEntryPoint,
            });
            if (result) setBundleResult(result);
          }}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-[#00d4ff] text-black rounded text-sm font-medium hover:bg-[#00b8e6] disabled:opacity-50"
        >
          Create Bundle
        </button>
      </div>

      {bundleResult && (
        <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
          <div className="text-sm font-medium text-[#00d4ff] mb-3">Bundle Info</div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(bundleResult).map(([key, value]) => (
              <div key={key} className="bg-[#0f0f23] rounded px-3 py-2">
                <span className="text-[#999] text-xs">{key.replace(/_/g, ' ')}</span>
                <div className="text-white text-xs font-mono mt-0.5">
                  {typeof value === 'number' ? value.toLocaleString() : String(value)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderGeneratedTab = () => (
    <div className="space-y-4">
      <div className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm font-medium text-[#00d4ff]">Generated Code ({filteredGenerated.length})</div>
          <div className="flex gap-2">
            <select value={genFilterDomain} onChange={(e) => setGenFilterDomain(e.target.value)} className="bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs">
              <option value="">All Domains</option>
              {DOMAINS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
            <select value={genFilterLanguage} onChange={(e) => setGenFilterLanguage(e.target.value)} className="bg-[#0f0f23] border border-[#2a2a4a] rounded px-2 py-1 text-white text-xs">
              <option value="">All Languages</option>
              {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
        </div>
        {filteredGenerated.length > 0 ? (
          <div className="space-y-2">
            {filteredGenerated.map((g) => (
              <div key={g.id} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <button
                    onClick={async () => {
                      if (viewCodeId === g.id) {
                        setViewCodeId(null);
                        setViewCodeDetail(null);
                      } else {
                        setViewCodeId(g.id);
                        setViewCodeDetail(g);
                      }
                    }}
                    className="text-white text-sm font-medium hover:text-[#00d4ff] text-left"
                  >
                    {g.name || g.id}
                  </button>
                  <div className="flex gap-1">
                    <span className="text-xs bg-[#1a1a2e] text-[#00d4ff] px-2 py-0.5 rounded">{g.language}</span>
                    <span className="text-xs bg-[#1a1a2e] text-[#ccc] px-2 py-0.5 rounded">{g.domain}</span>
                    {g.status && (
                      <span className={`text-xs px-2 py-0.5 rounded ${g.status === 'generated' ? 'bg-green-900 text-green-300' : g.status === 'reviewed' ? 'bg-blue-900 text-blue-300' : 'bg-[#1a1a1a] text-[#ccc]'}`}>
                        {g.status}
                      </span>
                    )}
                  </div>
                </div>
                {viewCodeId === g.id && viewCodeDetail && (
                  <div className="mt-2 bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-3">
                    {viewCodeDetail.description && (
                      <div className="text-[#999] text-xs mb-2">{viewCodeDetail.description}</div>
                    )}
                    <div className="bg-[#0f0f23] rounded overflow-hidden">
                      <pre className="text-green-400 text-xs font-mono p-3 whitespace-pre-wrap">
                        {(viewCodeDetail.code || '// Code content not available')
                          .split('\n')
                          .map((line: string, i: number) => (
                            <div key={i} className="flex">
                              <span className="text-[#555] w-8 text-right mr-3 select-none flex-shrink-0">{i + 1}</span>
                              <span>{line}</span>
                            </div>
                          ))}
                      </pre>
                    </div>
                    {viewCodeDetail.dependencies && viewCodeDetail.dependencies.length > 0 && (
                      <div className="mt-2">
                        <span className="text-xs text-[#999]">Dependencies: </span>
                        {viewCodeDetail.dependencies.map((d: string, i: number) => (
                          <span key={i} className="text-xs bg-[#0f0f23] text-[#00d4ff] px-2 py-0.5 rounded mr-1">{d}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[#999] text-xs">No generated code found. Use the Generate tab to create some.</div>
        )}
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded text-sm font-medium ${activeTab === tab.id ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div className={`mx-4 mt-3 px-4 py-2 rounded text-sm font-medium ${message.type === 'success' ? 'bg-green-900 text-green-300 border border-green-700' : 'bg-red-900 text-red-300 border border-red-700'}`}>
          {message.text}
        </div>
      )}

      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'status' && renderStatusTab()}
        {activeTab === 'templates' && renderTemplatesTab()}
        {activeTab === 'generate' && renderGenerateTab()}
        {activeTab === 'review' && renderReviewTab()}
        {activeTab === 'bundle' && renderBundleTab()}
        {activeTab === 'generated' && renderGeneratedTab()}
      </div>
    </div>
  );
};

export default AgentGameCodeGeneratorPanel;