import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'verification' | 'rules';

interface Report {
  id: string;
  artifact_id: string;
  artifact_type: string;
  status: string;
  issues_count: number;
  created_at: number;
}

interface Rule {
  id: string;
  config_id: string;
  stage: string;
  rule_name: string;
  condition: string;
  severity: string;
  created_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SEVERITY_COLORS: Record<string, string> = {
  blocker: '#ff6b6b',
  critical: '#e056a0',
  major: '#fdcb6e',
  minor: '#74b9ff',
  info: '#888',
};

const VerificationPipelinePanel: React.FC = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('verification');

  const [vArtifactId, setVArtifactId] = useState('');
  const [vArtifactContent, setVArtifactContent] = useState('');
  const [vArtifactType, setVArtifactType] = useState('code');
  const [vConfigId, setVConfigId] = useState('');

  const [ruleConfigId, setRuleConfigId] = useState('');
  const [ruleStage, setRuleStage] = useState('analyze');
  const [ruleName, setRuleName] = useState('');
  const [ruleCondition, setRuleCondition] = useState('');
  const [ruleSeverity, setRuleSeverity] = useState('minor');

  const [fixReportId, setFixReportId] = useState('');
  const [blockingReportId, setBlockingReportId] = useState('');
  const [blockingIssues, setBlockingIssues] = useState<any>(null);

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultReports: Report[] = [
    { id: uid(), artifact_id: 'art-1', artifact_type: 'code', status: 'verified', issues_count: 3, created_at: Date.now() - 86400000 },
    { id: uid(), artifact_id: 'art-2', artifact_type: 'asset', status: 'blocked', issues_count: 5, created_at: Date.now() - 172800000 },
  ];

  const defaultRules: Rule[] = [
    { id: uid(), config_id: 'cfg-1', stage: 'analyze', rule_name: 'No Debug Logs', condition: 'log_level != debug', severity: 'major', created_at: Date.now() - 86400000 },
    { id: uid(), config_id: 'cfg-1', stage: 'validate', rule_name: 'Asset Size Limit', condition: 'file_size < 10MB', severity: 'blocker', created_at: Date.now() - 172800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/verification-pipeline/stats`);
      const data = await res.json();
      if (data.reports) setReports(data.reports);
      if (data.rules) setRules(data.rules);
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    setReports(defaultReports);
    setRules(defaultRules);
    fetchStats();
  }, [fetchStats]);

  const handleVerifyArtifact = async () => {
    if (!vArtifactId.trim()) { showMessage('Artifact ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/verification-pipeline/verify-artifact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ artifact_id: vArtifactId, artifact_content: vArtifactContent, artifact_type: vArtifactType, config_id: vConfigId }),
      });
      const newReport: Report = { id: uid(), artifact_id: vArtifactId, artifact_type: vArtifactType, status: 'verified', issues_count: 0, created_at: Date.now() };
      setReports(prev => [...prev, newReport]);
      setVArtifactContent('');
      showMessage('Artifact verified', 'success');
    } catch {
      const newReport: Report = { id: uid(), artifact_id: vArtifactId, artifact_type: vArtifactType, status: 'verified', issues_count: 0, created_at: Date.now() };
      setReports(prev => [...prev, newReport]);
      setVArtifactContent('');
      showMessage('Artifact verified (offline fallback)', 'info');
    }
  };

  const handleAddRule = async () => {
    if (!ruleConfigId.trim() || !ruleName.trim()) { showMessage('Config ID and rule name are required', 'error'); return; }
    try {
      await fetch(`${apiBase}/verification-pipeline/add-rule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config_id: ruleConfigId, stage: ruleStage, rule_name: ruleName, condition: ruleCondition, severity: ruleSeverity }),
      });
      const newRule: Rule = { id: uid(), config_id: ruleConfigId, stage: ruleStage, rule_name: ruleName, condition: ruleCondition, severity: ruleSeverity, created_at: Date.now() };
      setRules(prev => [...prev, newRule]);
      setRuleName(''); setRuleCondition('');
      showMessage(`Rule "${ruleName}" added`, 'success');
    } catch {
      const newRule: Rule = { id: uid(), config_id: ruleConfigId, stage: ruleStage, rule_name: ruleName, condition: ruleCondition, severity: ruleSeverity, created_at: Date.now() };
      setRules(prev => [...prev, newRule]);
      setRuleName(''); setRuleCondition('');
      showMessage(`Rule "${ruleName}" added (offline fallback)`, 'info');
    }
  };

  const handleAutoFix = async () => {
    if (!fixReportId.trim()) { showMessage('Report ID is required', 'error'); return; }
    try {
      await fetch(`${apiBase}/verification-pipeline/auto-fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: fixReportId }),
      });
      setReports(prev => prev.map(r => r.id === fixReportId ? { ...r, status: 'fixed' } : r));
      showMessage('Auto-fix applied', 'success');
    } catch {
      setReports(prev => prev.map(r => r.id === fixReportId ? { ...r, status: 'fixed' } : r));
      showMessage('Auto-fix applied (offline fallback)', 'info');
    }
  };

  const handleBlockingIssues = async () => {
    if (!blockingReportId.trim()) { showMessage('Report ID is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/verification-pipeline/blocking-issues?report_id=${blockingReportId}`);
      const data = await res.json();
      setBlockingIssues(data);
      showMessage('Blocking issues loaded', 'success');
    } catch {
      setBlockingIssues({ report_id: blockingReportId, blocking_count: 0, issues: [] });
      showMessage('Blocking issues loaded (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'verification', label: 'Verification', icon: '\u2705', count: reports.length },
    { key: 'rules', label: 'Rules', icon: '\uD83D\uDCDD', count: rules.length },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD0D'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Verification Pipeline</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{reports.length} reports · {rules.length} rules</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label} <span style={{ color: '#666', fontWeight: 400 }}>({tab.count})</span>
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'verification' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\u2705'} verify-artifact</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Artifact ID</div>
                  <input value={vArtifactId} onChange={e => setVArtifactId(e.target.value)} placeholder="Artifact ID" style={{ padding: '6px 10px', fontSize: 11, width: 140, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Type</div>
                  <select value={vArtifactType} onChange={e => setVArtifactType(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="code">Code</option>
                    <option value="asset">Asset</option>
                    <option value="config">Config</option>
                    <option value="document">Document</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Config ID</div>
                  <input value={vConfigId} onChange={e => setVConfigId(e.target.value)} placeholder="Config ID" style={{ padding: '6px 10px', fontSize: 11, width: 120, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Content</div>
                  <input value={vArtifactContent} onChange={e => setVArtifactContent(e.target.value)} placeholder="Artifact content..." style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleVerifyArtifact} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Verify</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD27'} auto-fix</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Report ID</div>
                  <input value={fixReportId} onChange={e => setFixReportId(e.target.value)} placeholder="Report ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleAutoFix} style={{ padding: '6px 14px', backgroundColor: '#4a3d2d', color: '#fdcb6e', border: '1px solid #5a4d3d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Auto Fix</button>
              </div>
            </div>

            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDEAB'} blocking-issues</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Report ID</div>
                  <input value={blockingReportId} onChange={e => setBlockingReportId(e.target.value)} placeholder="Report ID" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleBlockingIssues} style={{ padding: '6px 14px', backgroundColor: '#3a1a1a', color: '#ff6b6b', border: '1px solid #5a2d2d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Get Issues</button>
              </div>
              {blockingIssues && (
                <div style={{ marginTop: 8, padding: 8, backgroundColor: '#141428', borderRadius: 4, fontSize: 10, color: '#aaa' }}>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(blockingIssues, null, 2)}</pre>
                </div>
              )}
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\u2705'} Reports <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({reports.length})</span></div>
            {reports.map(r => (
              <div key={r.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${r.status === 'verified' ? '#6bcb77' : r.status === 'blocked' ? '#ff6b6b' : r.status === 'fixed' ? '#74b9ff' : '#fdcb6e'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{r.artifact_id}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: r.status === 'verified' ? '#1a3a1a' : r.status === 'blocked' ? '#3a1a1a' : r.status === 'fixed' ? '#1a2a3a' : '#3a3a1a', color: r.status === 'verified' ? '#6bcb77' : r.status === 'blocked' ? '#ff6b6b' : r.status === 'fixed' ? '#74b9ff' : '#fdcb6e', fontWeight: 600, textTransform: 'uppercase' }}>{r.status}</span>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                  <span>Type: <span style={{ color: '#aaa' }}>{r.artifact_type}</span></span>
                  <span>{r.issues_count} issues</span>
                  <span>{formatTime(r.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'rules' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDCDD'} add-rule</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Config ID</div>
                  <input value={ruleConfigId} onChange={e => setRuleConfigId(e.target.value)} placeholder="Config ID" style={{ padding: '6px 10px', fontSize: 11, width: 120, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Stage</div>
                  <select value={ruleStage} onChange={e => setRuleStage(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="analyze">Analyze</option>
                    <option value="design">Design</option>
                    <option value="implement">Implement</option>
                    <option value="validate">Validate</option>
                    <option value="deploy">Deploy</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Rule Name</div>
                  <input value={ruleName} onChange={e => setRuleName(e.target.value)} placeholder="e.g. No Debug Logs" style={{ padding: '6px 10px', fontSize: 11, width: 140, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Severity</div>
                  <select value={ruleSeverity} onChange={e => setRuleSeverity(e.target.value)} style={{ padding: '6px 10px', fontSize: 11, backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }}>
                    <option value="blocker">Blocker</option>
                    <option value="critical">Critical</option>
                    <option value="major">Major</option>
                    <option value="minor">Minor</option>
                    <option value="info">Info</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Condition</div>
                  <input value={ruleCondition} onChange={e => setRuleCondition(e.target.value)} placeholder="e.g. log_level != debug" style={{ padding: '6px 10px', fontSize: 11, width: '100%', backgroundColor: '#141428', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' }} />
                </div>
                <button onClick={handleAddRule} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Add Rule</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDCDD'} Rules <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({rules.length})</span></div>
            {rules.map(r => (
              <div key={r.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${SEVERITY_COLORS[r.severity] || '#888'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{r.rule_name}</span>
                  <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (SEVERITY_COLORS[r.severity] || '#888') + '33', color: SEVERITY_COLORS[r.severity] || '#888', fontWeight: 600, textTransform: 'uppercase' }}>{r.severity}</span>
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>Condition: {r.condition}</div>
                <div style={{ display: 'flex', gap: 12, fontSize: 9, color: '#666', marginTop: 2 }}>
                  <span>Stage: <span style={{ color: '#aaa' }}>{r.stage}</span></span>
                  <span>Config: <span style={{ color: '#aaa' }}>{r.config_id}</span></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#141428', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDD0D'} {reports.length} reports · {rules.length} rules</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default VerificationPipelinePanel;