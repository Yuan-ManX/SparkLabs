import React, { useState, useCallback, useEffect } from 'react';
import { agentApi } from '../utils/api';

interface TestCase {
  test_id: string;
  test_type: string;
  description: string;
  severity: string;
}

interface TestResult {
  run_id: string;
  passed: number;
  failed: number;
  skipped: number;
  duration: number;
  results: { test_id: string; status: string; duration_ms: number }[];
}

const TYPE_COLORS: Record<string, string> = {
  smoke: '#10b981',
  regression: '#3b82f6',
  exploration: '#f97316',
  progression: '#8b5cf6',
  balance: '#ec4899',
  stress: '#ef4444',
};

const TestingDashboard: React.FC = () => {
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [results, setResults] = useState<TestResult | null>(null);
  const [coverage, setCoverage] = useState<Record<string, any> | null>(null);
  const [running, setRunning] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set(['smoke']));

  const loadStats = useCallback(async () => {
    try {
      const data = await agentApi.gameTestingStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ total_runs: 0, tests_defined: 0 });
    }
  }, []);

  const loadResults = useCallback(async () => {
    try {
      const data = await agentApi.gameTestingResults();
      setResults(data as TestResult);
    } catch { setResults(null); }
  }, []);

  const loadCoverage = useCallback(async () => {
    try {
      const data = await agentApi.gameTestingCoverage();
      setCoverage(data as Record<string, any>);
    } catch { setCoverage(null); }
  }, []);

  useEffect(() => { loadStats(); loadResults(); loadCoverage(); }, [loadStats, loadResults, loadCoverage]);

  const toggleType = (t: string) => {
    setSelectedTypes(prev => {
      const next = new Set(prev);
      next.has(t) ? next.delete(t) : next.add(t);
      return next;
    });
  };

  const handleRunTests = async () => {
    setRunning(true);
    try {
      const data = await agentApi.gameTestingRun(Array.from(selectedTypes));
      setResults(data as TestResult);
    } catch {}
    setRunning(false);
    loadStats();
  };

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#10b981' }}>Testing Dashboard</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 70 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Total Runs</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.total_runs || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 70 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Tests Defined</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.tests_defined || 0}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
        {['smoke', 'regression', 'exploration', 'progression', 'balance', 'stress'].map(t => (
          <button
            key={t}
            onClick={() => toggleType(t)}
            style={{
              padding: '4px 10px', borderRadius: 6, fontSize: 11,
              border: selectedTypes.has(t) ? `2px solid ${TYPE_COLORS[t]}` : '1px solid #333',
              background: selectedTypes.has(t) ? '#1a2a1a' : '#1a1a2e',
              color: selectedTypes.has(t) ? TYPE_COLORS[t] : '#888',
              cursor: 'pointer',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <button
        onClick={handleRunTests}
        disabled={running}
        style={{
          padding: '8px 20px', borderRadius: 6, border: 'none',
          background: running ? '#333' : '#10b981', color: '#fff',
          cursor: running ? 'default' : 'pointer', fontSize: 13, marginBottom: 16,
        }}
      >
        {running ? 'Running...' : 'Run Tests'}
      </button>

      {results && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
            <span style={{ color: '#10b981', fontSize: 13 }}>Passed: {results.passed || 0}</span>
            <span style={{ color: '#ef4444', fontSize: 13 }}>Failed: {results.failed || 0}</span>
            <span style={{ color: '#888', fontSize: 13 }}>Skipped: {results.skipped || 0}</span>
          </div>
          {results.results?.slice(0, 10).map((r, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', padding: '4px 8px',
              background: '#1a1a2e', borderRadius: 4, marginBottom: 3, fontSize: 11,
            }}>
              <span style={{ color: r.status === 'passed' ? '#10b981' : '#ef4444' }}>{r.status}</span>
              <span style={{ color: '#888' }}>{r.test_id}</span>
              <span style={{ color: '#888' }}>{r.duration_ms}ms</span>
            </div>
          ))}
        </div>
      )}

      {coverage && (
        <div style={{ padding: 10, background: '#1a1a2e', borderRadius: 6 }}>
          <div style={{ fontSize: 12, color: '#aaa', marginBottom: 6 }}>Coverage Report</div>
          {Object.entries(coverage).map(([key, val]) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '2px 0' }}>
              <span style={{ color: '#e0e0e0' }}>{key}</span>
              <span style={{ color: '#8b5cf6' }}>{typeof val === 'number' ? val + '%' : String(val)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TestingDashboard;