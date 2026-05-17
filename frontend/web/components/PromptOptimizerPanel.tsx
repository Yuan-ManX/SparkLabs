import React, { useState, useEffect, useCallback } from 'react';

type PromptDomain = 'game_generation' | 'level_design' | 'character_creation' | 'code_generation' | 'balancing' | 'ui_design' | 'sound_design' | 'narrative' | 'testing' | 'general';

interface PromptTemplateData {
  id: string;
  name: string;
  domain: string;
  template_text: string;
  system_prompt: string;
  variables: string[];
  temperature: number;
  max_tokens: number;
  usage_count: number;
  avg_quality: number;
}

interface OptimizationRule {
  id: string;
  rule_name: string;
  domain: string;
  condition_description: string;
  transformation: string;
  priority: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const DOMAINS: PromptDomain[] = [
  'game_generation', 'level_design', 'character_creation', 'code_generation',
  'balancing', 'ui_design', 'sound_design', 'narrative', 'testing', 'general',
];

const DOMAIN_LABELS: Record<string, string> = {
  game_generation: 'Game Gen',
  level_design: 'Level Design',
  character_creation: 'Characters',
  code_generation: 'Code',
  balancing: 'Balancing',
  ui_design: 'UI Design',
  sound_design: 'Sound',
  narrative: 'Narrative',
  testing: 'Testing',
  general: 'General',
};

const DOMAIN_COLORS: Record<string, string> = {
  game_generation: '#6c5ce7',
  level_design: '#00b894',
  character_creation: '#e17055',
  code_generation: '#0984e3',
  balancing: '#fdcb6e',
  ui_design: '#a29bfe',
  sound_design: '#fd79a8',
  narrative: '#55efc4',
  testing: '#74b9ff',
  general: '#636e72',
};

const PromptOptimizerPanel: React.FC = () => {
  const [templates, setTemplates] = useState<PromptTemplateData[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplateData | null>(null);
  const [fillValues, setFillValues] = useState<Record<string, string>>({});
  const [filledResult, setFilledResult] = useState<string>('');
  const [domainFilter, setDomainFilter] = useState<string>('');
  const [stats, setStats] = useState<any>(null);
  const [sessionQuality, setSessionQuality] = useState<number>(0.8);
  const [sessionResponse, setSessionResponse] = useState<string>('');
  const [rules, setRules] = useState<OptimizationRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const showMessage = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchTemplates = useCallback(async () => {
    const url = domainFilter
      ? `${apiBase}/prompt-optimizer/list-templates?domain=${domainFilter}`
      : `${apiBase}/prompt-optimizer/list-templates`;
    try {
      const res = await fetch(url);
      const data = await res.json();
      setTemplates(data.templates || []);
    } catch {}
  }, [domainFilter]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/prompt-optimizer/stats`);
      const data = await res.json();
      setStats(data);
    } catch {}
  }, []);

  const fetchRules = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/prompt-optimizer/list-rules`);
      const data = await res.json();
      setRules(data.rules || []);
    } catch {}
  }, []);

  useEffect(() => {
    fetchTemplates();
    fetchStats();
    fetchRules();
  }, [fetchTemplates, fetchStats, fetchRules]);

  const handleSelectTemplate = (tmpl: PromptTemplateData) => {
    setSelectedTemplate(tmpl);
    const values: Record<string, string> = {};
    (tmpl.variables || []).forEach(v => { values[v] = ''; });
    setFillValues(values);
    setFilledResult('');
  };

  const handleFill = async () => {
    if (!selectedTemplate) return;
    setLoading(true);
    try {
      const varsJson = encodeURIComponent(JSON.stringify(fillValues));
      const res = await fetch(
        `${apiBase}/prompt-optimizer/fill-template?template_id=${selectedTemplate.id}&variables=${varsJson}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setFilledResult(data.filled_prompt || '');
    } catch {
      showMessage('Fill failed', 'error');
    }
    setLoading(false);
  };

  const handleRecordSession = async () => {
    if (!selectedTemplate || !filledResult) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({
        template_id: selectedTemplate.id,
        filled_prompt: filledResult,
        response_text: sessionResponse || 'Generated content',
        quality_score: String(sessionQuality),
        latency_ms: '1200',
        domain: selectedTemplate.domain,
      });
      await fetch(`${apiBase}/prompt-optimizer/record-session?${params}`, { method: 'POST' });
      showMessage('Session recorded', 'success');
      fetchTemplates();
    } catch {
      showMessage('Session recording failed', 'error');
    }
    setLoading(false);
  };

  const handleOptimize = async () => {
    if (!selectedTemplate) return;
    setLoading(true);
    try {
      const res = await fetch(
        `${apiBase}/prompt-optimizer/optimize-template?template_id=${selectedTemplate.id}`,
        { method: 'POST' }
      );
      const data = await res.json();
      showMessage(`Optimization analysis complete: ${JSON.stringify(data).slice(0, 100)}...`, 'success');
    } catch {
      showMessage('Optimization failed', 'error');
    }
    setLoading(false);
  };

  const handleGetBest = async () => {
    try {
      const domain = domainFilter || 'game_generation';
      const res = await fetch(`${apiBase}/prompt-optimizer/get-best-template?domain=${domain}`);
      const tmpl = await res.json();
      if (tmpl.id) handleSelectTemplate(tmpl);
    } catch {
      showMessage('Could not fetch best template', 'error');
    }
  };

  const handleFillVariable = (key: string, value: string) => {
    setFillValues(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#1a1a2e',
      color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif',
      fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid #2a2a3e',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <i className="fa-solid fa-wand-magic-sparkles" style={{ color: '#6c5ce7', fontSize: 16 }} />
          <span style={{ fontWeight: 700, fontSize: 15 }}>Prompt Optimizer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 11, color: '#888' }}>
              {stats.template_count} templates | {stats.session_count} sessions
            </span>
          )}
          <button
            onClick={() => { fetchTemplates(); fetchStats(); }}
            style={{
              background: 'none', border: '1px solid #333', color: '#aaa',
              borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: 12,
            }}
          >
            <i className="fa-solid fa-rotate" />
          </button>
        </div>
      </div>

      {/* Message toast */}
      {message && (
        <div style={{
          padding: '8px 16px',
          backgroundColor: message.type === 'success' ? '#1a3a1a' : '#3a1a1a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : '#5a2d2d'}`,
          color: message.type === 'success' ? '#6bcb77' : '#ff6b6b',
          fontSize: 12,
        }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left sidebar - template list */}
        <div style={{
          width: 260,
          borderRight: '1px solid #2a2a3e',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}>
          {/* Domain filter */}
          <div style={{ padding: '8px 12px', borderBottom: '1px solid #2a2a3e' }}>
            <select
              value={domainFilter}
              onChange={e => setDomainFilter(e.target.value)}
              style={{
                width: '100%', padding: '6px 8px',
                backgroundColor: '#2a2a3e', color: '#e0e0e0',
                border: '1px solid #333', borderRadius: 4, fontSize: 12,
              }}
            >
              <option value="">All Domains</option>
              {DOMAINS.map(d => (
                <option key={d} value={d}>{DOMAIN_LABELS[d]}</option>
              ))}
            </select>
          </div>

          {/* Quick actions */}
          <div style={{ padding: '8px 12px', borderBottom: '1px solid #2a2a3e', display: 'flex', gap: 6 }}>
            <button
              onClick={handleGetBest}
              style={{
                flex: 1, padding: '5px 8px', fontSize: 11,
                backgroundColor: '#2d2d4a', color: '#a29bfe',
                border: '1px solid #3d3d5a', borderRadius: 4, cursor: 'pointer',
              }}
            >
              <i className="fa-solid fa-star" style={{ marginRight: 4 }} />
              Best
            </button>
          </div>

          {/* Template list */}
          <div style={{ flex: 1, overflow: 'auto' }}>
            {templates.length === 0 && (
              <div style={{ padding: 20, textAlign: 'center', color: '#666', fontSize: 12 }}>
                No templates found
              </div>
            )}
            {templates.map(tmpl => (
              <div
                key={tmpl.id}
                onClick={() => handleSelectTemplate(tmpl)}
                style={{
                  padding: '10px 12px',
                  cursor: 'pointer',
                  borderBottom: '1px solid #22223a',
                  backgroundColor: selectedTemplate?.id === tmpl.id ? '#2d2d4a' : 'transparent',
                  borderLeft: `3px solid ${selectedTemplate?.id === tmpl.id ? '#6c5ce7' : 'transparent'}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <span style={{
                    fontSize: 10, padding: '2px 6px', borderRadius: 3,
                    backgroundColor: DOMAIN_COLORS[tmpl.domain] + '33',
                    color: DOMAIN_COLORS[tmpl.domain],
                    fontWeight: 600,
                  }}>
                    {DOMAIN_LABELS[tmpl.domain] || tmpl.domain}
                  </span>
                </div>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>
                  {tmpl.name}
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>
                  {tmpl.variables?.length || 0} vars | used {tmpl.usage_count}x | quality {tmpl.avg_quality.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right content area */}
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
          {!selectedTemplate ? (
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              height: '100%', color: '#555', flexDirection: 'column', gap: 10,
            }}>
              <i className="fa-solid fa-file-lines" style={{ fontSize: 40, opacity: 0.3 }} />
              <span>Select a prompt template to edit</span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Template info */}
              <div style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <span style={{
                    padding: '3px 8px', borderRadius: 3, fontSize: 11,
                    backgroundColor: DOMAIN_COLORS[selectedTemplate.domain] + '33',
                    color: DOMAIN_COLORS[selectedTemplate.domain],
                    fontWeight: 600,
                  }}>
                    {DOMAIN_LABELS[selectedTemplate.domain]}
                  </span>
                  <span style={{ fontWeight: 700, fontSize: 16 }}>{selectedTemplate.name}</span>
                </div>
                <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
                  Temp: {selectedTemplate.temperature} | Max Tokens: {selectedTemplate.max_tokens}
                </div>
                <div style={{
                  padding: '8px 12px', backgroundColor: '#1a1a2e', borderRadius: 4,
                  fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap',
                  border: '1px solid #2a2a3e', color: '#bbb',
                }}>
                  {selectedTemplate.system_prompt && (
                    <div style={{ marginBottom: 6, color: '#a29bfe', fontSize: 11, fontWeight: 600 }}>
                      SYSTEM PROMPT:
                    </div>
                  )}
                  {selectedTemplate.system_prompt}
                  <div style={{ marginTop: 8, borderTop: '1px solid #2a2a3e', paddingTop: 6 }}>
                    {selectedTemplate.template_text}
                  </div>
                </div>
              </div>

              {/* Variable fill form */}
              {selectedTemplate.variables.length > 0 && (
                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 8,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontWeight: 600, marginBottom: 10, fontSize: 14 }}>
                    Variables
                    <span style={{ fontSize: 11, marginLeft: 8 }}>
                      ({selectedTemplate.variables.length})
                    </span>
                  </div>
                  {selectedTemplate.variables.map(varName => (
                    <div key={varName} style={{
                      display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8,
                    }}>
                      <span style={{
                        fontSize: 12, fontWeight: 600, color: '#6c5ce7',
                        minWidth: 120, fontFamily: 'monospace',
                      }}>
                        {'{{'}{varName}{'}}'}
                      </span>
                      <input
                        value={fillValues[varName] || ''}
                        onChange={e => handleFillVariable(varName, e.target.value)}
                        placeholder={`Enter ${varName}...`}
                        style={{
                          flex: 1, padding: '6px 10px',
                          backgroundColor: '#1a1a2e', color: '#e0e0e0',
                          border: '1px solid #333', borderRadius: 4, fontSize: 12,
                        }}
                      />
                    </div>
                  ))}
                  <button
                    onClick={handleFill}
                    disabled={loading}
                    style={{
                      marginTop: 8, padding: '8px 16px',
                      backgroundColor: '#6c5ce7', color: '#fff',
                      border: 'none', borderRadius: 6, cursor: 'pointer',
                      fontSize: 13, fontWeight: 600, opacity: loading ? 0.6 : 1,
                    }}
                  >
                    <i className="fa-solid fa-fill" style={{ marginRight: 6 }} />
                    {loading ? 'Filling...' : 'Fill Template'}
                  </button>
                </div>
              )}

              {/* Filled result */}
              {filledResult && (
                <div style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 8,
                  border: '1px solid #2a2a3e',
                }}>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>
                    <i className="fa-solid fa-check-circle" style={{ color: '#6bcb77', marginRight: 6 }} />
                    Filled Result
                  </div>
                  <div style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                    fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap',
                    border: '1px solid #2a2a3e', color: '#ddd',
                    maxHeight: 200, overflow: 'auto',
                  }}>
                    {filledResult}
                  </div>

                  {/* Session recording */}
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8, color: '#aaa' }}>
                      Record Session Feedback
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                      <span style={{ fontSize: 11, color: '#888', minWidth: 50 }}>Quality:</span>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={sessionQuality}
                        onChange={e => setSessionQuality(parseFloat(e.target.value))}
                        style={{ flex: 1 }}
                      />
                      <span style={{
                        fontSize: 12, fontWeight: 600,
                        color: sessionQuality >= 0.8 ? '#6bcb77' : sessionQuality >= 0.5 ? '#fdcb6e' : '#ff6b6b',
                        minWidth: 30,
                      }}>
                        {sessionQuality.toFixed(2)}
                      </span>
                    </div>
                    <textarea
                      value={sessionResponse}
                      onChange={e => setSessionResponse(e.target.value)}
                      placeholder="Add session response / feedback here..."
                      rows={3}
                      style={{
                        width: '100%', padding: '8px 10px',
                        backgroundColor: '#1a1a2e', color: '#e0e0e0',
                        border: '1px solid #333', borderRadius: 4, fontSize: 12,
                        resize: 'vertical', fontFamily: 'system-ui, sans-serif',
                      }}
                    />
                    <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                      <button
                        onClick={handleRecordSession}
                        disabled={loading}
                        style={{
                          padding: '7px 14px',
                          backgroundColor: '#2d2d4a', color: '#a29bfe',
                          border: '1px solid #3d3d5a', borderRadius: 6,
                          cursor: 'pointer', fontSize: 12, fontWeight: 600,
                          opacity: loading ? 0.6 : 1,
                        }}
                      >
                        <i className="fa-solid fa-floppy-disk" style={{ marginRight: 5 }} />
                        Record Session
                      </button>
                      <button
                        onClick={handleOptimize}
                        disabled={loading}
                        style={{
                          padding: '7px 14px',
                          backgroundColor: '#2d2d4a', color: '#fdcb6e',
                          border: '1px solid #3d3d5a', borderRadius: 6,
                          cursor: 'pointer', fontSize: 12, fontWeight: 600,
                          opacity: loading ? 0.6 : 1,
                        }}
                      >
                        <i className="fa-solid fa-microscope" style={{ marginRight: 5 }} />
                        Analyze & Optimize
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Stats summary */}
              <div style={{
                padding: '10px 14px', backgroundColor: '#1e1e32', borderRadius: 6,
                display: 'flex', gap: 20, fontSize: 11, color: '#888',
                border: '1px solid #22223a',
              }}>
                <span>
                  <i className="fa-solid fa-chart-simple" style={{ marginRight: 4 }} />
                  Usage: {selectedTemplate.usage_count}
                </span>
                <span>
                  <i className="fa-solid fa-star" style={{ marginRight: 4 }} />
                  Quality: {selectedTemplate.avg_quality.toFixed(2)}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom status bar */}
      <div style={{
        padding: '6px 12px',
        borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          <i className="fa-solid fa-database" style={{ marginRight: 4 }} />
          {stats ? `${stats.template_count} templates · ${stats.session_count} sessions` : 'Loading...'}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {rules.length > 0 && (
            <span>
              <i className="fa-solid fa-ruler" style={{ marginRight: 3 }} />
              {rules.length} optimization rules
            </span>
          )}
        </span>
      </div>
    </div>
  );
};

export default PromptOptimizerPanel;