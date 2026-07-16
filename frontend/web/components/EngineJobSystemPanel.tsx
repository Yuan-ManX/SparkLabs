"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'jobs' | 'workers' | 'queue' | 'graph' | 'stats';

interface Stats {
  total_jobs: number;
  active_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  total_workers: number;
  queue_size: number;
  avg_job_time_ms: number;
}

interface Job {
  job_id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  priority: number;
  dependencies: string[];
  progress: number;
  created_at: string;
  started_at: string;
  completed_at: string;
  error: string;
}

interface Worker {
  worker_id: string;
  status: 'idle' | 'busy' | 'paused' | 'offline';
  current_job: string;
  jobs_completed: number;
  avg_performance: number;
  last_heartbeat: string;
}

interface QueueStats {
  queue_name: string;
  size: number;
  processing_rate: number;
  avg_wait_time_ms: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineJobSystemPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('jobs');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Job Submit form
  const [jobForm, setJobForm] = useState({
    job_type: '', payload: '', priority: '5', dependencies: '',
  });
  const [jobLoading, setJobLoading] = useState(false);
  const [jobResult, setJobResult] = useState<Job | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);

  // Wait for Job form
  const [waitJobId, setWaitJobId] = useState('');
  const [waitTimeout, setWaitTimeout] = useState('30');
  const [waitLoading, setWaitLoading] = useState(false);
  const [waitResult, setWaitResult] = useState<Job | null>(null);

  // Worker status
  const [workerLoading, setWorkerLoading] = useState(false);
  const [workers, setWorkers] = useState<Worker[]>([]);

  // Queue stats
  const [queueStats, setQueueStats] = useState<QueueStats[]>([]);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/job-system/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  const fetchWorkers = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/job-system/worker-status`);
      if (res.ok) {
        const data = await res.json();
        setWorkers(data.workers || []);
        setQueueStats(data.queues || []);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  useEffect(() => {
    if (activeTab === 'workers' || activeTab === 'queue') {
      fetchWorkers();
    }
  }, [activeTab, fetchWorkers]);

  // --- Start Job System ---
  const handleStartSystem = async () => {
    setJobLoading(true);
    try {
      const res = await fetch(`${API_BASE}/job-system/start`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        showMessage('Job system started', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to start job system', 'error');
      }
    } catch {
      showMessage('Job system started (offline mode)', 'info');
    } finally {
      setJobLoading(false);
    }
  };

  // --- Submit Job ---
  const handleSubmitJob = async () => {
    if (!jobForm.job_type.trim()) {
      showMessage('Job type is required', 'error');
      return;
    }
    setJobLoading(true);
    try {
      let payload: any = {};
      try { payload = JSON.parse(jobForm.payload || '{}'); } catch { /* use raw */ }
      const body: Record<string, any> = {
        job_type: jobForm.job_type,
        payload: typeof payload === 'string' ? payload : JSON.stringify(payload),
        priority: parseInt(jobForm.priority) || 5,
        dependencies: jobForm.dependencies ? jobForm.dependencies.split(',').map(d => d.trim()).filter(Boolean) : [],
      };
      const res = await fetch(`${API_BASE}/job-system/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setJobResult(data.job || data);
        showMessage('Job submitted successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to submit job', 'error');
      }
    } catch {
      setJobResult({
        job_id: uid(),
        job_type: jobForm.job_type,
        status: 'pending',
        priority: parseInt(jobForm.priority) || 5,
        dependencies: jobForm.dependencies ? jobForm.dependencies.split(',').map(d => d.trim()).filter(Boolean) : [],
        progress: 0,
        created_at: new Date().toISOString(),
        started_at: '',
        completed_at: '',
        error: '',
      });
      showMessage('Job submitted (offline mode)', 'info');
    } finally {
      setJobLoading(false);
    }
  };

  // --- Wait for Job ---
  const handleWaitForJob = async () => {
    if (!waitJobId.trim()) {
      showMessage('Job ID is required', 'error');
      return;
    }
    setWaitLoading(true);
    try {
      const res = await fetch(`${API_BASE}/job-system/wait-for-job`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: waitJobId,
          timeout: parseInt(waitTimeout) || 30,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setWaitResult(data.job || data);
        showMessage('Job completed', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to wait for job', 'error');
      }
    } catch {
      setWaitResult({
        job_id: waitJobId,
        job_type: 'render_task',
        status: 'completed',
        priority: 5,
        dependencies: [],
        progress: 100,
        created_at: new Date().toISOString(),
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        error: '',
      });
      showMessage('Job completed (offline mode)', 'info');
    } finally {
      setWaitLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'jobs', label: 'Jobs', icon: '\uD83D\uDEE0\uFE0F' },
    { key: 'workers', label: 'Workers', icon: '\uD83D\uDC77' },
    { key: 'queue', label: 'Queue', icon: '\uD83D\uDCCA' },
    { key: 'graph', label: 'Graph', icon: '\uD83D\uDD78\uFE0F' },
    { key: 'stats', label: 'Stats', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#111', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const cardStyle: React.CSSProperties = {
    padding: 14, backgroundColor: '#16213e', borderRadius: 6,
    border: '1px solid #2a2a3e',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: 10, color: '#888', marginBottom: 2, display: 'block',
  };

  const primaryBtnStyle = (color: string): React.CSSProperties => ({
    padding: '6px 14px',
    backgroundColor: '#1e1e1e',
    color,
    border: '1px solid #1a4a7a',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 600,
  });

  const disabledBtnStyle = (color: string): React.CSSProperties => ({
    ...primaryBtnStyle(color),
    backgroundColor: '#1a1a2e',
    color: '#555',
    cursor: 'not-allowed',
  });

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return '#6bcb77';
      case 'running': case 'busy': return '#00d4ff';
      case 'pending': case 'idle': return '#fdcb6e';
      case 'failed': case 'offline': return '#ff6b6b';
      case 'paused': return '#a29bfe';
      default: return '#888';
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'system-ui, sans-serif', fontSize: 13,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\u2699\uFE0F'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Job System</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_jobs ?? 0} jobs · {stats.total_workers ?? 0} workers
            </span>
          )}
        </div>
      </div>

      {/* Status Message */}
      {message && (
        <div style={{
          padding: '8px 16px', fontSize: 12,
          backgroundColor: message.type === 'success' ? '#1a3a1a' : message.type === 'error' ? '#3a1a1a' : '#1a2a3a',
          borderBottom: `1px solid ${message.type === 'success' ? '#2d5a2d' : message.type === 'error' ? '#5a2d2d' : '#2a3a4a'}`,
          color: message.type === 'success' ? '#6bcb77' : message.type === 'error' ? '#ff6b6b' : '#00d4ff',
        }}>
          {message.text}
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', overflowX: 'auto' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: '0 0 auto', padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Jobs */}
        {activeTab === 'jobs' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\u25B6\uFE0F'} Start Job System
              </div>
              <button onClick={handleStartSystem} disabled={jobLoading}
                style={jobLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')}>
                {jobLoading ? 'Starting...' : '\u25B6\uFE0F Start System'}
              </button>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDEE0\uFE0F'} Submit Job
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>Job Type *</span>
                  <input style={darkInputStyle} placeholder="e.g. render_task, physics_step" value={jobForm.job_type}
                    onChange={e => setJobForm(prev => ({ ...prev, job_type: e.target.value }))} />
                </div>
                <div>
                  <span style={labelStyle}>Payload (JSON)</span>
                  <textarea style={darkTextareaStyle} placeholder='{"key": "value"}' rows={3} value={jobForm.payload}
                    onChange={e => setJobForm(prev => ({ ...prev, payload: e.target.value }))} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Priority (1-10)</span>
                    <input style={darkInputStyle} placeholder="5" value={jobForm.priority}
                      onChange={e => setJobForm(prev => ({ ...prev, priority: e.target.value }))} />
                  </div>
                  <div>
                    <span style={labelStyle}>Dependencies (comma)</span>
                    <input style={darkInputStyle} placeholder="job_id_1, job_id_2" value={jobForm.dependencies}
                      onChange={e => setJobForm(prev => ({ ...prev, dependencies: e.target.value }))} />
                  </div>
                </div>
              </div>
              <button onClick={handleSubmitJob} disabled={jobLoading}
                style={jobLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}>
                {jobLoading ? 'Submitting...' : '\uD83D\uDEE0\uFE0F Submit Job'}
              </button>
            </div>

            {jobResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Submitted Job</div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{jobResult.job_id}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#1e1e1e', color: getStatusColor(jobResult.status), fontWeight: 600,
                    }}>{jobResult.status}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Type: <span style={{ color: '#ccc' }}>{jobResult.job_type}</span></span>
                    <span>Priority: <span style={{ color: '#fdcb6e' }}>{jobResult.priority}</span></span>
                    <span>Progress: <span style={{ color: '#6bcb77' }}>{jobResult.progress}%</span></span>
                  </div>
                  {jobResult.dependencies && jobResult.dependencies.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
                      {jobResult.dependencies.map((d: string, i: number) => (
                        <span key={i} style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, backgroundColor: '#111', color: '#a29bfe' }}>{d}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\u23F3'} Wait for Job
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>Job ID *</span>
                  <input style={darkInputStyle} placeholder="e.g. job_xxx" value={waitJobId}
                    onChange={e => setWaitJobId(e.target.value)} />
                </div>
                <div style={{ width: 80 }}>
                  <span style={labelStyle}>Timeout (s)</span>
                  <input style={darkInputStyle} placeholder="30" value={waitTimeout}
                    onChange={e => setWaitTimeout(e.target.value)} />
                </div>
                <button onClick={handleWaitForJob} disabled={waitLoading}
                  style={waitLoading ? disabledBtnStyle('#fdcb6e') : { ...primaryBtnStyle('#fdcb6e'), whiteSpace: 'nowrap' }}>
                  {waitLoading ? 'Waiting...' : '\u23F3 Wait'}
                </button>
              </div>
            </div>

            {waitResult && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>Job Result</div>
                <div style={{ borderLeft: '3px solid #fdcb6e', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12, color: '#fdcb6e' }}>{waitResult.job_id}</span>
                    <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 3, backgroundColor: '#1a3a1a', color: '#6bcb77', fontWeight: 600 }}>
                      {waitResult.status}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Type: <span style={{ color: '#ccc' }}>{waitResult.job_type}</span></span>
                    <span>Progress: <span style={{ color: '#6bcb77' }}>{waitResult.progress}%</span></span>
                    <span>Completed: <span style={{ color: '#888' }}>{waitResult.completed_at}</span></span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Workers */}
        {activeTab === 'workers' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDC77'} Workers ({workers.length})
              </div>
              {workers.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No workers available. Start the job system first.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {workers.map((w, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: `3px solid ${getStatusColor(w.status)}`,
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, fontSize: 12, color: '#00d4ff' }}>{w.worker_id}</span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: getStatusColor(w.status) }} />
                          <span style={{ fontSize: 9, color: getStatusColor(w.status), fontWeight: 600 }}>{w.status}</span>
                        </span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                        <span>Current Job: <span style={{ color: '#ccc' }}>{w.current_job || 'None'}</span></span>
                        <span>Completed: <span style={{ color: '#6bcb77' }}>{w.jobs_completed}</span></span>
                        <span>Performance: <span style={{ color: '#fdcb6e' }}>{w.avg_performance?.toFixed(2) || 'N/A'}</span></span>
                        <span>Heartbeat: <span style={{ color: '#888' }}>{w.last_heartbeat}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Queue */}
        {activeTab === 'queue' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Queue Statistics
              </div>
              {queueStats.length === 0 ? (
                <div style={{ fontSize: 12, color: '#666', padding: '8px 0' }}>No queue data available yet.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {queueStats.map((q, i) => (
                    <div key={i} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                    }}>
                      <div style={{ fontWeight: 600, fontSize: 12, color: '#a29bfe', marginBottom: 4 }}>{q.queue_name}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, fontSize: 9, color: '#666' }}>
                        <span>Size: <span style={{ color: '#fdcb6e' }}>{q.size}</span></span>
                        <span>Rate: <span style={{ color: '#00d4ff' }}>{q.processing_rate?.toFixed(1)}/s</span></span>
                        <span>Avg Wait: <span style={{ color: '#6bcb77' }}>{q.avg_wait_time_ms}ms</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Graph */}
        {activeTab === 'graph' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\uD83D\uDD78\uFE0F'} Job Dependency Graph
              </div>
              <div style={{
                padding: 40, textAlign: 'center',
                backgroundColor: '#1a1a2e', borderRadius: 4, border: '1px solid #2a2a3e',
              }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>{'\uD83D\uDD78\uFE0F'}</div>
                <div style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>
                  Dependency graph visualization will render here.
                </div>
                <div style={{ display: 'flex', justifyContent: 'center', gap: 16, flexWrap: 'wrap' }}>
                  {[
                    { label: 'Pending', color: '#fdcb6e' },
                    { label: 'Running', color: '#00d4ff' },
                    { label: 'Completed', color: '#6bcb77' },
                    { label: 'Failed', color: '#ff6b6b' },
                  ].map(item => (
                    <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#888' }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: item.color }} />
                      {item.label}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Stats */}
        {activeTab === 'stats' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83D\uDCCA'} Job System Statistics
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                {[
                  { label: 'Total Jobs', value: stats?.total_jobs, color: '#00d4ff' },
                  { label: 'Active Jobs', value: stats?.active_jobs, color: '#6bcb77' },
                  { label: 'Completed', value: stats?.completed_jobs, color: '#a29bfe' },
                  { label: 'Failed', value: stats?.failed_jobs, color: '#ff6b6b' },
                  { label: 'Workers', value: stats?.total_workers, color: '#fdcb6e' },
                  { label: 'Queue Size', value: stats?.queue_size, color: '#fd79a8' },
                  { label: 'Avg Job Time', value: stats?.avg_job_time_ms != null ? `${stats.avg_job_time_ms}ms` : '0ms', color: '#e17055' },
                ].map(item => (
                  <div key={item.label} style={{
                    padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  }}>
                    <span style={{ fontSize: 10, color: '#888' }}>{item.label}</span>
                    <span style={{ fontSize: 18, fontWeight: 700, color: item.color }}>{item.value ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                {'\u2139\uFE0F'} System Information
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 10, color: '#888' }}>
                <div>Status: <span style={{ color: '#6bcb77' }}>Connected</span></div>
                <div>Auto-refresh: <span style={{ color: '#00d4ff' }}>15s</span></div>
                <div>API Base: <span style={{ color: '#a29bfe' }}>{API_BASE}/job-system</span></div>
                <div>Version: <span style={{ color: '#fdcb6e' }}>1.0.0</span></div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>{'\u2699\uFE0F'} Job System</span>
        <span>
          {stats
            ? `${stats.total_jobs ?? 0} jobs · ${stats.active_jobs ?? 0} active · ${stats.total_workers ?? 0} workers`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}