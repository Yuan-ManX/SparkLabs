import React, { useState, useEffect, useCallback } from 'react';
import { validatorApi } from '../utils/api';

type TabType = 'validate' | 'rules' | 'reports';

const SEVERITY_COLORS: Record<string, string> = {
  info: '#3b82f6',
  warning: '#f59e0b',
  error: '#ef4444',
  critical: '#dc2626',
};

const CATEGORY_ICONS: Record<string, string> = {
  code_style: 'fa-code',
  code_logic: 'fa-brain',
  asset_integrity: 'fa-image',
  game_rules: 'fa-chess',
  configuration: 'fa-gear',
  performance: 'fa-gauge-high',
  security: 'fa-shield',
  compatibility: 'fa-puzzle-piece',
  naming: 'fa-font',
  structure: 'fa-sitemap',
};

const ValidationPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('validate');
  const [rules, setRules] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [codeInput, setCodeInput] = useState('');
  const [validationResult, setValidationResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadRules = useCallback(async () => {
    try {
      const res = await validatorApi.listRules();
      setRules((res as any)?.rules || (res as any) || []);
    } catch (e) { /* ignore */ }
  }, []);

  const loadReports = useCallback(async () => {
    try {
      const res = await validatorApi.reports();
      setReports((res as any)?.reports || (res as any) || []);
    } catch (e) { /* ignore */ }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const res = await validatorApi.stats();
      setStats(res);
    } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => {
    loadRules();
    loadReports();
    loadStats();
  }, [loadRules, loadReports, loadStats]);

  const handleValidate = async () => {
    if (!codeInput.trim()) return;
    setLoading(true);
    try {
      const res = await validatorApi.validateCode(codeInput);
      setValidationResult(res);
      loadReports();
      loadStats();
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  const handleToggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      await validatorApi.toggleRule(ruleId, !enabled);
      loadRules();
    } catch (e) { /* ignore */ }
  };

  const handleAutoFix = async (reportId: string) => {
    try {
      await validatorApi.autoFix(reportId, codeInput);
    } catch (e) { /* ignore */ }
  };

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'validate', label: 'Validate', icon: 'fa-check-circle' },
    { key: 'rules', label: 'Rules', icon: 'fa-list-check' },
    { key: 'reports', label: 'Reports', icon: 'fa-file-lines' },
  ];

  return (
    <div className="h-full flex flex-col bg-[#111] text-[#e0e0e0]">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1e1e1e]">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] transition-colors ${
              activeTab === tab.key
                ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30'
                : 'text-[#888] hover:text-[#ccc] hover:bg-[#1a1a1a]'
            }`}
          >
            <i className={`fa-solid ${tab.icon} text-[10px]`} />
            {tab.label}
          </button>
        ))}
        <div className="flex-1" />
        {stats && (
          <div className="flex items-center gap-3 text-[10px] text-[#666]">
            <span>{stats.total_rules || 0} rules</span>
            <span>{stats.total_issues_found || 0} issues found</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'validate' && (
          <div className="space-y-4">
            <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
              <h4 className="text-[11px] font-semibold text-[#999] mb-2">Code Input</h4>
              <textarea
                value={codeInput}
                onChange={e => setCodeInput(e.target.value)}
                placeholder="Paste code here to validate..."
                className="w-full h-40 bg-[#151515] border border-[#2a2a2a] rounded px-3 py-2 text-[11px] text-[#e0e0e0] font-mono placeholder-[#555] focus:border-orange-500/50 focus:outline-none resize-none"
              />
              <button
                onClick={handleValidate}
                disabled={loading}
                className="mt-2 flex items-center gap-1.5 px-4 py-1.5 bg-green-600 text-white rounded text-[11px] hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                <i className="fa-solid fa-play text-[9px]" />
                {loading ? 'Validating...' : 'Validate Code'}
              </button>
            </div>

            {validationResult && (
              <div className="space-y-3">
                <div className="grid grid-cols-4 gap-3">
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <div className="text-[10px] text-[#666] mb-1">Score</div>
                    <div className="text-[20px] font-bold" style={{
                      color: validationResult.score >= 80 ? '#22c55e' : validationResult.score >= 50 ? '#f59e0b' : '#ef4444'
                    }}>
                      {validationResult.score?.toFixed(0)}%
                    </div>
                  </div>
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <div className="text-[10px] text-[#666] mb-1">Issues</div>
                    <div className="text-[20px] font-bold text-yellow-400">{validationResult.issue_count || 0}</div>
                  </div>
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <div className="text-[10px] text-[#666] mb-1">Passed</div>
                    <div className={`text-[20px] font-bold ${validationResult.passed ? 'text-green-400' : 'text-red-400'}`}>
                      {validationResult.passed ? 'Yes' : 'No'}
                    </div>
                  </div>
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <div className="text-[10px] text-[#666] mb-1">Duration</div>
                    <div className="text-[20px] font-bold text-blue-400">{validationResult.duration_ms?.toFixed(0)}ms</div>
                  </div>
                </div>

                {validationResult.by_severity && (
                  <div className="flex gap-2">
                    {Object.entries(validationResult.by_severity).map(([sev, count]) => (
                      <span key={sev} className="text-[10px] px-2 py-1 rounded"
                        style={{ backgroundColor: (SEVERITY_COLORS[sev] || '#666') + '20', color: SEVERITY_COLORS[sev] || '#666' }}>
                        {sev}: {count as number}
                      </span>
                    ))}
                  </div>
                )}

                {validationResult.issues && validationResult.issues.length > 0 && (
                  <div className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-[11px] font-semibold text-[#999]">Issues</h4>
                      {validationResult.id && (
                        <button
                          onClick={() => handleAutoFix(validationResult.id)}
                          className="px-2 py-1 bg-blue-600/20 text-blue-400 rounded text-[10px] hover:bg-blue-600/30 transition-colors"
                        >
                          Auto Fix
                        </button>
                      )}
                    </div>
                    <div className="space-y-1.5">
                      {validationResult.issues.map((issue: any, i: number) => (
                        <div key={issue.id || i} className="p-2 bg-[#151515] rounded">
                          <div className="flex items-center gap-2">
                            <span className="text-[9px] px-1.5 py-0.5 rounded"
                              style={{ backgroundColor: (SEVERITY_COLORS[issue.severity] || '#666') + '20', color: SEVERITY_COLORS[issue.severity] || '#666' }}>
                              {issue.severity}
                            </span>
                            <i className={`fa-solid ${CATEGORY_ICONS[issue.category] || 'fa-circle'} text-[9px] text-[#555]`} />
                            <span className="text-[10px] text-[#ccc] flex-1">{issue.message}</span>
                          </div>
                          {issue.line && (
                            <div className="text-[9px] text-[#555] mt-1 ml-8">
                              Line {issue.line}{issue.column ? `:${issue.column}` : ''} · {issue.category}
                              {issue.fix_type !== 'none' && (
                                <span className="ml-2 text-blue-400">fix: {issue.fix_type}</span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'rules' && (
          <div className="space-y-2">
            {rules.map((rule: any) => (
              <div key={rule.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <i className={`fa-solid ${CATEGORY_ICONS[rule.category] || 'fa-circle'} text-[10px]`}
                      style={{ color: SEVERITY_COLORS[rule.severity] || '#666' }} />
                    <span className="text-[12px] font-medium">{rule.name}</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: (SEVERITY_COLORS[rule.severity] || '#666') + '20', color: SEVERITY_COLORS[rule.severity] || '#666' }}>
                      {rule.severity}
                    </span>
                    {rule.auto_fixable && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-900/30 text-blue-400">auto-fix</span>
                    )}
                  </div>
                  <button
                    onClick={() => handleToggleRule(rule.id, rule.enabled)}
                    className={`w-8 h-4 rounded-full transition-colors ${rule.enabled ? 'bg-green-600' : 'bg-[#333]'}`}
                  >
                    <div className={`w-3 h-3 rounded-full bg-white transition-transform ${rule.enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
                  </button>
                </div>
                <p className="text-[10px] text-[#888] mt-1">{rule.description}</p>
                <div className="text-[9px] text-[#555] mt-1">
                  {rule.category} · {rule.scope} · {rule.pattern ? `pattern: ${rule.pattern.substring(0, 30)}` : 'custom check'}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'reports' && (
          <div className="space-y-2">
            {reports.length === 0 ? (
              <div className="text-center py-12 text-[#555] text-[12px]">
                <i className="fa-solid fa-file-lines text-[24px] mb-2 text-[#333]" />
                <p>No validation reports yet</p>
              </div>
            ) : (
              reports.map((report: any) => (
                <div key={report.id} className="bg-[#0a0a0a] rounded-lg border border-[#2a2a2a] p-3">
                  <div className="flex items-center gap-2">
                    <span className={`text-[12px] font-medium ${report.passed ? 'text-green-400' : 'text-red-400'}`}>
                      {report.passed ? '✓' : '✗'} {report.target}
                    </span>
                    <span className="text-[10px] text-[#555]">{report.target_type}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-[10px] text-[#666]">
                    <span>Score: <span style={{ color: report.score >= 80 ? '#22c55e' : '#f59e0b' }}>{report.score?.toFixed(0)}%</span></span>
                    <span>Issues: {report.issue_count}</span>
                    <span>Rules: {report.rules_checked}</span>
                    <span>{report.duration_ms?.toFixed(0)}ms</span>
                  </div>
                  {report.by_severity && (
                    <div className="flex gap-1.5 mt-1.5">
                      {Object.entries(report.by_severity).map(([sev, count]) => (
                        <span key={sev} className="text-[8px] px-1.5 py-0.5 rounded"
                          style={{ backgroundColor: (SEVERITY_COLORS[sev] || '#666') + '20', color: SEVERITY_COLORS[sev] || '#666' }}>
                          {sev}: {count as number}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ValidationPanel;
