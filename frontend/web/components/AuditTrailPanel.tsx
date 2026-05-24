import React, { useState, useEffect, useCallback } from 'react';

type TabId = 'events' | 'query' | 'report';

interface AuditEvent {
  id: string;
  agent_id: string;
  event_type: string;
  description: string;
  details: string;
  severity: string;
  timestamp: number;
}

interface AuditReport {
  id: string;
  time_range_days: number;
  total_events: number;
  severity_breakdown: { severity: string; count: number }[];
  top_event_types: { event_type: string; count: number }[];
  generated_at: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const SEVERITY_COLORS: Record<string, string> = {
  info: '#74b9ff',
  warning: '#fdcb6e',
  error: '#ff6b6b',
  critical: '#e056a0',
};

const AuditTrailPanel: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [queryResults, setQueryResults] = useState<AuditEvent[]>([]);
  const [reports, setReports] = useState<AuditReport[]>([]);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>('events');

  const [eventAgentId, setEventAgentId] = useState('');
  const [eventType, setEventType] = useState('action');
  const [eventDesc, setEventDesc] = useState('');
  const [eventDetails, setEventDetails] = useState('');
  const [eventSeverity, setEventSeverity] = useState('info');

  const [queryAgentId, setQueryAgentId] = useState('');
  const [queryEventType, setQueryEventType] = useState('');
  const [queryLimit, setQueryLimit] = useState('50');

  const [reportDays, setReportDays] = useState('7');

  const apiBase = 'http://localhost:8000/api/agent';

  const defaultEvents: AuditEvent[] = [
    { id: uid(), agent_id: 'agent-001', event_type: 'action', description: 'Agent invoked tool: search_codebase', details: 'Query: "find all React components"', severity: 'info', timestamp: Date.now() - 300000 },
    { id: uid(), agent_id: 'agent-001', event_type: 'config_change', description: 'Temperature updated from 0.7 to 0.3', details: 'User-initiated change', severity: 'warning', timestamp: Date.now() - 600000 },
    { id: uid(), agent_id: 'agent-002', event_type: 'error', description: 'API rate limit exceeded', details: 'OpenAI API returned 429', severity: 'error', timestamp: Date.now() - 900000 },
    { id: uid(), agent_id: 'agent-001', event_type: 'action', description: 'File modified: GameEditor.tsx', details: 'Added dark mode toggle component', severity: 'info', timestamp: Date.now() - 1200000 },
    { id: uid(), agent_id: 'agent-003', event_type: 'security', description: 'Unauthorized access attempt blocked', details: 'Invalid API key from IP 192.168.1.100', severity: 'critical', timestamp: Date.now() - 1500000 },
  ];

  const defaultReports: AuditReport[] = [
    {
      id: uid(), time_range_days: 7, total_events: 342,
      severity_breakdown: [{ severity: 'info', count: 280 }, { severity: 'warning', count: 45 }, { severity: 'error', count: 14 }, { severity: 'critical', count: 3 }],
      top_event_types: [{ event_type: 'action', count: 210 }, { event_type: 'config_change', count: 68 }, { event_type: 'error', count: 45 }],
      generated_at: Date.now() - 3600000,
    },
  ];

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/audit-trail/stats`);
      const data = await res.json();
      if (data.events) setEvents(data.events);
    } catch {
      // use defaults
    }
  }, []);

  useEffect(() => {
    setEvents(defaultEvents);
    setReports(defaultReports);
    fetchStats();
  }, [fetchStats]);

  const handleLogEvent = async () => {
    if (!eventAgentId.trim() || !eventDesc.trim()) {
      showMessage('Agent ID and description are required', 'error');
      return;
    }
    try {
      await fetch(`${apiBase}/audit-trail/log-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: eventAgentId,
          event_type: eventType,
          description: eventDesc,
          details: eventDetails,
          severity: eventSeverity,
        }),
      });
      const newEvent: AuditEvent = {
        id: uid(),
        agent_id: eventAgentId,
        event_type: eventType,
        description: eventDesc,
        details: eventDetails,
        severity: eventSeverity,
        timestamp: Date.now(),
      };
      setEvents(prev => [newEvent, ...prev]);
      setEventDesc('');
      setEventDetails('');
      showMessage('Event logged successfully', 'success');
    } catch {
      const newEvent: AuditEvent = {
        id: uid(),
        agent_id: eventAgentId,
        event_type: eventType,
        description: eventDesc,
        details: eventDetails,
        severity: eventSeverity,
        timestamp: Date.now(),
      };
      setEvents(prev => [newEvent, ...prev]);
      setEventDesc('');
      setEventDetails('');
      showMessage('Event logged (offline fallback)', 'info');
    }
  };

  const handleQuery = async () => {
    try {
      const params = new URLSearchParams();
      if (queryAgentId) params.set('agent_id', queryAgentId);
      if (queryEventType) params.set('event_type', queryEventType);
      if (queryLimit) params.set('limit', queryLimit);
      const res = await fetch(`${apiBase}/audit-trail/query?${params.toString()}`);
      const data = await res.json();
      if (data.events) setQueryResults(data.events);
      showMessage(`Query returned ${data.events?.length || 0} events`, 'success');
    } catch {
      setQueryResults(events.filter(e => {
        if (queryAgentId && e.agent_id !== queryAgentId) return false;
        if (queryEventType && e.event_type !== queryEventType) return false;
        return true;
      }).slice(0, parseInt(queryLimit) || 50));
      showMessage('Query completed (offline fallback)', 'info');
    }
  };

  const handleGenerateReport = async () => {
    try {
      const res = await fetch(`${apiBase}/audit-trail/generate-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_range_days: parseInt(reportDays) }),
      });
      const data = await res.json();
      if (data) {
        setReports(prev => [data, ...prev]);
      }
      showMessage('Report generated', 'success');
    } catch {
      const report: AuditReport = {
        id: uid(),
        time_range_days: parseInt(reportDays),
        total_events: events.length,
        severity_breakdown: [
          { severity: 'info', count: events.filter(e => e.severity === 'info').length },
          { severity: 'warning', count: events.filter(e => e.severity === 'warning').length },
          { severity: 'error', count: events.filter(e => e.severity === 'error').length },
          { severity: 'critical', count: events.filter(e => e.severity === 'critical').length },
        ],
        top_event_types: [{ event_type: 'action', count: 15 }, { event_type: 'config_change', count: 5 }],
        generated_at: Date.now(),
      };
      setReports(prev => [report, ...prev]);
      showMessage('Report generated (offline fallback)', 'info');
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const tabItems: { key: TabId; label: string; icon: string; count: number }[] = [
    { key: 'events', label: 'Events', icon: '\uD83D\uDCDD', count: events.length },
    { key: 'query', label: 'Query', icon: '\uD83D\uDD0D', count: queryResults.length },
    { key: 'report', label: 'Reports', icon: '\uD83D\uDCCA', count: reports.length },
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
          <span style={{ fontSize: 18 }}>{'\uD83D\uDCDD'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Audit Trail</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#888' }}>
            {events.length} events · {reports.length} reports
          </span>
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
        {activeTab === 'events' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCDD'} log-event
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Agent ID</div>
                  <input value={eventAgentId} onChange={e => setEventAgentId(e.target.value)} placeholder="e.g. agent-001" style={{
                    padding: '6px 10px', fontSize: 11, width: 100,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Event Type</div>
                  <select value={eventType} onChange={e => setEventType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="action">Action</option>
                    <option value="config_change">Config Change</option>
                    <option value="error">Error</option>
                    <option value="security">Security</option>
                    <option value="system">System</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Severity</div>
                  <select value={eventSeverity} onChange={e => setEventSeverity(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="info">Info</option>
                    <option value="warning">Warning</option>
                    <option value="error">Error</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
                <div style={{ flex: 1, minWidth: 150 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Description</div>
                  <input value={eventDesc} onChange={e => setEventDesc(e.target.value)} placeholder="What happened?" style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Details</div>
                  <input value={eventDetails} onChange={e => setEventDetails(e.target.value)} placeholder="Additional details..." style={{
                    padding: '6px 10px', fontSize: 11, width: '100%',
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleLogEvent} style={{
                  padding: '6px 14px', backgroundColor: '#2d4a2d', color: '#6bcb77',
                  border: '1px solid #3d5a3d', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Log Event</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDCDD'} Audit Events <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({events.length})</span>
            </div>
            {events.map(event => (
              <div key={event.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${SEVERITY_COLORS[event.severity] || '#888'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{event.agent_id}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: (SEVERITY_COLORS[event.severity] || '#888') + '33',
                      color: SEVERITY_COLORS[event.severity] || '#888', fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{event.severity}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#141428', color: '#aaa', fontWeight: 600,
                    }}>{event.event_type}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(event.timestamp)}</span>
                </div>
                <div style={{ fontSize: 11, color: '#ccc', marginBottom: 2 }}>{event.description}</div>
                {event.details && (
                  <div style={{ fontSize: 10, color: '#888', fontStyle: 'italic' }}>{event.details}</div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === 'query' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDD0D'} query
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Agent ID</div>
                  <input value={queryAgentId} onChange={e => setQueryAgentId(e.target.value)} placeholder="e.g. agent-001" style={{
                    padding: '6px 10px', fontSize: 11, width: 110,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Event Type</div>
                  <select value={queryEventType} onChange={e => setQueryEventType(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }}>
                    <option value="">All</option>
                    <option value="action">Action</option>
                    <option value="config_change">Config Change</option>
                    <option value="error">Error</option>
                    <option value="security">Security</option>
                  </select>
                </div>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Limit</div>
                  <input value={queryLimit} onChange={e => setQueryLimit(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 60,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleQuery} style={{
                  padding: '6px 14px', backgroundColor: '#2d3a5a', color: '#74b9ff',
                  border: '1px solid #3d4a6a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Search</button>
              </div>
            </div>

            <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>
              {'\uD83D\uDD0D'} Query Results <span style={{ fontSize: 10, color: '#888', marginLeft: 4 }}>({queryResults.length})</span>
            </div>
            {queryResults.length > 0 ? queryResults.map(event => (
              <div key={event.id} style={{
                padding: 10, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${SEVERITY_COLORS[event.severity] || '#888'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>{event.agent_id}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: (SEVERITY_COLORS[event.severity] || '#888') + '33',
                      color: SEVERITY_COLORS[event.severity] || '#888', fontWeight: 600,
                      textTransform: 'uppercase',
                    }}>{event.severity}</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(event.timestamp)}</span>
                </div>
                <div style={{ fontSize: 11, color: '#ccc' }}>{event.description}</div>
              </div>
            )) : (
              <div style={{
                textAlign: 'center', padding: 40, color: '#555',
                backgroundColor: '#22223a', borderRadius: 8, border: '1px solid #2a2a3e',
              }}>
                <span style={{ fontSize: 40, opacity: 0.3, display: 'block', marginBottom: 10 }}>{'\uD83D\uDD0D'}</span>
                Run a query to see results
              </div>
            )}
          </div>
        )}

        {activeTab === 'report' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              padding: 12, backgroundColor: '#22223a', borderRadius: 6,
              border: '1px solid #2a2a3e',
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#aaa', marginBottom: 8 }}>
                {'\uD83D\uDCCA'} generate-report
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>Time Range (days)</div>
                  <input value={reportDays} onChange={e => setReportDays(e.target.value)} style={{
                    padding: '6px 10px', fontSize: 11, width: 80,
                    backgroundColor: '#141428', color: '#ccc',
                    border: '1px solid #333', borderRadius: 4, outline: 'none',
                  }} />
                </div>
                <button onClick={handleGenerateReport} style={{
                  padding: '6px 14px', backgroundColor: '#4a2d4a', color: '#e056a0',
                  border: '1px solid #5a3d5a', borderRadius: 4, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600,
                }}>Generate Report</button>
              </div>
            </div>

            {reports.map(report => (
              <div key={report.id} style={{
                padding: 14, backgroundColor: '#22223a', borderRadius: 8,
                border: '1px solid #2a2a3e', borderLeft: '3px solid #e056a0',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: '#e056a0' }}>
                    {'\uD83D\uDCCA'} Audit Report ({report.time_range_days}d)
                  </span>
                  <span style={{ fontSize: 10, color: '#666' }}>{formatTime(report.generated_at)}</span>
                </div>
                <div style={{ fontSize: 11, color: '#aaa', marginBottom: 10 }}>
                  Total Events: <span style={{ color: '#74b9ff', fontWeight: 600 }}>{report.total_events}</span>
                </div>
                <div style={{ fontSize: 11, color: '#aaa', fontWeight: 600, marginBottom: 6 }}>Severity Breakdown</div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
                  {report.severity_breakdown.map(sb => (
                    <div key={sb.severity} style={{
                      padding: '4px 10px', borderRadius: 4, fontSize: 10,
                      backgroundColor: (SEVERITY_COLORS[sb.severity] || '#888') + '33',
                      color: SEVERITY_COLORS[sb.severity] || '#888',
                      border: `1px solid ${SEVERITY_COLORS[sb.severity] || '#888'}44`,
                    }}>
                      {sb.severity.toUpperCase()}: <span style={{ fontWeight: 600 }}>{sb.count}</span>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 11, color: '#aaa', fontWeight: 600, marginBottom: 6 }}>Top Event Types</div>
                {report.top_event_types.map(tet => (
                  <div key={tet.event_type} style={{
                    display: 'flex', justifyContent: 'space-between', padding: '4px 8px',
                    backgroundColor: '#141428', borderRadius: 3, marginBottom: 3, fontSize: 10,
                  }}>
                    <span style={{ color: '#ccc' }}>{tet.event_type}</span>
                    <span style={{ color: '#fdcb6e', fontWeight: 600 }}>{tet.count}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#141428', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\uD83D\uDCDD'} {events.length} events · {reports.length} reports</span>
        <span>Connected</span>
      </div>
    </div>
  );
};

export default AuditTrailPanel;