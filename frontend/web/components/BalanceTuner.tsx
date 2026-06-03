import React, { useState, useCallback, useEffect } from 'react';
import { agentApi } from '../utils/api';

interface BalanceParameter {
  name: string;
  domain: string;
  current_value: number;
  target_min?: number;
  target_max?: number;
  sensitivity: number;
}

interface BalanceReport {
  domain: string;
  status: string;
  parameters: BalanceParameter[];
  recommendations: string[];
}

const DOMAIN_COLORS: Record<string, string> = {
  combat: '#ef4444',
  economy: '#10b981',
  progression: '#8b5cf6',
  spawning: '#f97316',
};

const BalanceTuner: React.FC = () => {
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [parameters, setParameters] = useState<BalanceParameter[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>('combat');
  const [analyzing, setAnalyzing] = useState(false);
  const [report, setReport] = useState<BalanceReport | null>(null);
  const [message, setMessage] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const data = await agentApi.balancerStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ parameters_tracked: 0, analyses_run: 0 });
    }
  }, []);

  const loadParameters = useCallback(async () => {
    try {
      const data = await agentApi.balancerParameters(selectedDomain);
      setParameters(((data as any).parameters as BalanceParameter[]) || []);
    } catch {
      setParameters([]);
    }
  }, [selectedDomain]);

  useEffect(() => { loadStats(); }, [loadStats]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      const data = await agentApi.balancerAnalyze(selectedDomain);
      setReport(data as BalanceReport);
      setMessage(`Analysis complete for ${selectedDomain}`);
    } catch {
      setMessage('Analysis failed. Check backend connection.');
    }
    setAnalyzing(false);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'balanced': return '#10b981';
      case 'undertuned': return '#3b82f6';
      case 'overtuned': return '#f97316';
      case 'broken': return '#ef4444';
      default: return '#888';
    }
  };

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#f97316' }}>Balance Tuner</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          {Object.entries(stats).map(([key, value]) => (
            <div key={key} style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6, minWidth: 80 }}>
              <div style={{ fontSize: 11, color: '#888' }}>{key.replace(/_/g, ' ')}</div>
              <div style={{ fontSize: 18, fontWeight: 'bold' }}>{String(value)}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['combat', 'economy', 'progression', 'spawning'].map(domain => (
          <button
            key={domain}
            onClick={() => { setSelectedDomain(domain); setReport(null); loadParameters(); }}
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              border: selectedDomain === domain ? `2px solid ${DOMAIN_COLORS[domain]}` : '1px solid #333',
              background: selectedDomain === domain ? '#2a1a0a' : '#1a1a2e',
              color: selectedDomain === domain ? DOMAIN_COLORS[domain] : '#aaa',
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            {domain.charAt(0).toUpperCase() + domain.slice(1)}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          style={{
            padding: '8px 20px',
            borderRadius: 6,
            border: 'none',
            background: analyzing ? '#333' : '#f97316',
            color: '#fff',
            cursor: analyzing ? 'default' : 'pointer',
            fontSize: 13,
          }}
        >
          {analyzing ? 'Analyzing...' : 'Analyze Domain'}
        </button>
      </div>

      {message && (
        <div style={{ padding: 8, marginBottom: 12, background: '#1a2a1a', borderRadius: 6, color: '#10b981', fontSize: 12 }}>
          {message}
        </div>
      )}

      {report && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <span style={{ fontSize: 13, color: '#aaa' }}>Status:</span>
            <span style={{
              padding: '2px 8px',
              borderRadius: 4,
              background: getStatusColor(report.status) + '22',
              color: getStatusColor(report.status),
              fontSize: 12,
              fontWeight: 'bold',
            }}>
              {report.status.toUpperCase()}
            </span>
          </div>

          {report.recommendations && report.recommendations.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: '#aaa', marginBottom: 6 }}>Recommendations:</div>
              {report.recommendations.map((rec, i) => (
                <div key={i} style={{ padding: '4px 8px', fontSize: 11, color: '#e0e0e0', background: '#1a1a2e', borderRadius: 4, marginBottom: 4 }}>
                  {rec}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {parameters.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>Parameters ({parameters.length})</div>
          {parameters.map((param, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '6px 10px', background: '#1a1a2e', borderRadius: 4, marginBottom: 4, fontSize: 12
            }}>
              <span style={{ color: '#e0e0e0' }}>{param.name}</span>
              <span style={{ color: '#f97316' }}>{param.current_value?.toFixed(2)}</span>
              <span style={{ color: '#888', fontSize: 10 }}>
                s={param.sensitivity?.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BalanceTuner;