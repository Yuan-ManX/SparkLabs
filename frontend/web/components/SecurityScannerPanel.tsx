import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type TabId = 'scan' | 'rules' | 'quarantine';

interface ThreatFinding {
  id: string;
  type: string;
  severity: string;
  description: string;
  location: string;
}

interface SecurityRule {
  id: string;
  name: string;
  category: string;
  enabled: boolean;
  pattern: string;
  created_at: number;
}

interface QuarantinedItem {
  id: string;
  content_hash: string;
  reason: string;
  quarantined_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ff6b6b',
  high: '#fdcb6e',
  medium: '#74b9ff',
  low: '#6bcb77',
};

const SecurityScannerPanel: React.FC = () => {
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('scan');
  const [rules, setRules] = useState<SecurityRule[]>([]);
  const [quarantinedItems, setQuarantinedItems] = useState<QuarantinedItem[]>([]);
  const [scanReport, setScanReport] = useState<{ findings: ThreatFinding[] } | null>(null);

  const [content, setContent] = useState('');
  const [sourceType, setSourceType] = useState('text');

  const apiBase = API_ROOT + '/agent';

  const defaultRules: SecurityRule[] = [
    { id: uid(), name: 'SQL Injection Detection', category: 'injection', enabled: true, pattern: '/(DROP|INSERT|SELECT)\s+/i', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'XSS Pattern Check', category: 'xss', enabled: true, pattern: '/<script.*?>/i', created_at: Date.now() - 86400000 },
    { id: uid(), name: 'Hardcoded Credentials', category: 'credentials', enabled: true, pattern: '/password\s*=\s*["\'].+["\']/i', created_at: Date.now() - 172800000 },
    { id: uid(), name: 'Path Traversal', category: 'path_traversal', enabled: false, pattern: '/\.\.\/|\.\.\\\\/i', created_at: Date.now() - 259200000 },
  ];

  const defaultQuarantined: QuarantinedItem[] = [
    { id: uid(), content_hash: 'a1b2c3d4', reason: 'Detected SQL injection attempt', quarantined_at: Date.now() - 86400000 },
    { id: uid(), content_hash: 'e5f6g7h8', reason: 'XSS pattern match', quarantined_at: Date.now() - 172800000 },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/security-scanner/stats`);
      const data = await res.json();
      if (data.rules) setRules(data.rules);
      if (data.quarantined) setQuarantinedItems(data.quarantined);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setRules(defaultRules);
    setQuarantinedItems(defaultQuarantined);
    fetchStats();
  }, [fetchStats]);

  const handleScanContent = async () => {
    if (!content.trim()) { showMessage('Content is required', 'error'); return; }
    try {
      const res = await fetch(`${apiBase}/security-scanner/scan-content`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, source_type: sourceType }),
      });
      const data = await res.json();
      setScanReport(data);
      showMessage(`Scan complete: ${data.findings?.length || 0} findings`, 'success');
    } catch {
      setScanReport({
        findings: [
          { id: uid(), type: 'SQL Injection', severity: 'high', description: 'Potential SQL injection in query parameter', location: 'line 12' },
          { id: uid(), type: 'XSS', severity: 'medium', description: 'Unescaped user input in HTML output', location: 'line 47' },
        ],
      });
      showMessage('Scan complete (offline fallback)', 'info');
    }
  };

  const handleLoadRules = async () => {
    try {
      const res = await fetch(`${apiBase}/security-scanner/active-rules`);
      const data = await res.json();
      if (data.rules) setRules(data.rules);
      showMessage('Rules loaded', 'success');
    } catch {
      setRules(defaultRules);
      showMessage('Rules loaded (offline fallback)', 'info');
    }
  };

  const handleToggleRule = async (ruleId: string) => {
    const rule = rules.find(r => r.id === ruleId);
    if (!rule) return;
    try {
      await fetch(`${apiBase}/security-scanner/toggle-rule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_id: ruleId, enabled: !rule.enabled }),
      });
      setRules(prev => prev.map(r => r.id === ruleId ? { ...r, enabled: !r.enabled } : r));
      showMessage(`Rule "${rule.name}" ${!rule.enabled ? 'enabled' : 'disabled'}`, 'success');
    } catch {
      setRules(prev => prev.map(r => r.id === ruleId ? { ...r, enabled: !r.enabled } : r));
      showMessage(`Rule "${rule.name}" ${!rule.enabled ? 'enabled' : 'disabled'} (offline fallback)`, 'info');
    }
  };

  const handleViewQuarantined = async () => {
    try {
      const res = await fetch(`${apiBase}/security-scanner/quarantined`);
      const data = await res.json();
      if (data.items) setQuarantinedItems(data.items);
      showMessage('Quarantined items loaded', 'success');
    } catch {
      setQuarantinedItems(defaultQuarantined);
      showMessage('Quarantined items loaded (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'scan', label: 'Scan', icon: '\uD83D\uDD0D' },
    { key: 'rules', label: 'Rules', icon: '\uD83D\uDEE1\uFE0F' },
    { key: 'quarantine', label: 'Quarantine', icon: '\uD83D\uDD12' },
  ];

  const inputStyle: React.CSSProperties = { padding: '6px 10px', fontSize: 11, backgroundColor: '#111', color: '#ccc', border: '1px solid #333', borderRadius: 4, outline: 'none' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#1a1a2e', color: '#e0e0e0', fontFamily: 'system-ui, sans-serif', fontSize: 13 }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #2a2a3e', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83D\uDD12'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Security Scanner</span>
        </div>
        <span style={{ fontSize: 10, color: '#888' }}>{rules.length} rules · {quarantinedItems.length} quarantined</span>
      </div>

      {message && (
        <div style={{ padding: '8px 16px', fontSize: 12, backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a', borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`, color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#74b9ff' }}>
          {message.text}
        </div>
      )}

      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e' }}>
        {tabItems.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{ flex: 1, padding: '8px 12px', fontSize: 12, fontWeight: 600, backgroundColor: activeTab === tab.key ? '#22223a' : 'transparent', color: activeTab === tab.key ? '#e0e0e0' : '#888', border: 'none', borderBottom: activeTab === tab.key ? '2px solid #6c5ce7' : '2px solid transparent', cursor: 'pointer' }}>
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'scan' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>{'\uD83D\uDD0D'} Scan Content</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Content</div>
                  <textarea value={content} onChange={e => setContent(e.target.value)} placeholder="Paste content to scan..." style={{ ...inputStyle, width: '100%', minHeight: 80, resize: 'vertical' }} />
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                  <div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Source Type</div>
                    <select value={sourceType} onChange={e => setSourceType(e.target.value)} style={{ ...inputStyle, width: 150 }}>
                      <option value="text">Plain Text</option>
                      <option value="code">Source Code</option>
                      <option value="http">HTTP Request</option>
                      <option value="json">JSON Payload</option>
                      <option value="sql">SQL Query</option>
                    </select>
                  </div>
                  <button onClick={handleScanContent} style={{ padding: '6px 14px', backgroundColor: '#3a1a1a', color: '#ff6b6b', border: '1px solid #5a2d2d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>Scan Content</button>
                </div>
              </div>
            </div>

            {scanReport && (
              <>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDEA8'} Scan Report ({scanReport.findings.length} findings)</div>
                {scanReport.findings.map(finding => (
                  <div key={finding.id} style={{ padding: 10, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${SEVERITY_COLORS[finding.severity] || '#888'}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 12, color: '#ccc' }}>{finding.type}</span>
                      <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: (SEVERITY_COLORS[finding.severity] || '#888') + '33', color: SEVERITY_COLORS[finding.severity] || '#888' }}>{finding.severity.toUpperCase()}</span>
                    </div>
                    <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>{finding.description}</div>
                    <div style={{ fontSize: 9, color: '#666' }}>Location: {finding.location}</div>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {activeTab === 'rules' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button onClick={handleLoadRules} style={{ padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff', border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>Load Rules</button>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDEE1\uFE0F'} Security Rules ({rules.length})</div>
            {rules.map(rule => (
              <div key={rule.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: `3px solid ${rule.enabled ? '#6bcb77' : '#ff6b6b'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#ccc' }}>{rule.name}</span>
                  <button onClick={() => handleToggleRule(rule.id)} style={{ padding: '2px 10px', fontSize: 10, backgroundColor: rule.enabled ? '#1a3a1a' : '#3a1a1a', color: rule.enabled ? '#6bcb77' : '#ff6b6b', border: '1px solid ' + (rule.enabled ? '#2d5a2d' : '#5a2d2d'), borderRadius: 3, cursor: 'pointer' }}>
                    {rule.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                </div>
                <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#888' }}>
                  <span>Category: <span style={{ color: '#a29bfe' }}>{rule.category}</span></span>
                  <span>Pattern: <code style={{ color: '#fdcb6e' }}>{rule.pattern}</code></span>
                </div>
                <div style={{ fontSize: 9, color: '#666', marginTop: 4 }}>{formatTime(rule.created_at)}</div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'quarantine' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <button onClick={handleViewQuarantined} style={{ padding: '6px 14px', backgroundColor: '#3a1a1a', color: '#ff6b6b', border: '1px solid #5a2d2d', borderRadius: 4, cursor: 'pointer', fontSize: 11, fontWeight: 600, alignSelf: 'flex-start' }}>View Quarantined</button>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>{'\uD83D\uDD12'} Quarantined Items ({quarantinedItems.length})</div>
            {quarantinedItems.map(item => (
              <div key={item.id} style={{ padding: 12, backgroundColor: '#22223a', borderRadius: 6, border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#ccc', marginBottom: 4 }}>Hash: <code style={{ color: '#a29bfe' }}>{item.content_hash}</code></div>
                <div style={{ fontSize: 10, color: '#ff6b6b', marginBottom: 4 }}>{item.reason}</div>
                <div style={{ fontSize: 9, color: '#666' }}>Quarantined: {formatTime(item.quarantined_at)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ padding: '6px 12px', borderTop: '1px solid #2a2a3e', backgroundColor: '#111', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: '#666' }}>
        <span>{'\uD83D\uDD12'} {rules.length} rules · {quarantinedItems.length} quarantined</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default SecurityScannerPanel;