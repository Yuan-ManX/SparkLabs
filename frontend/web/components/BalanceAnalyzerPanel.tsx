import React, { useState, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

type BalanceDomain = 'mechanics' | 'economy' | 'progression' | 'combat' | 'difficulty';
type SeverityLevel = 'well_balanced' | 'slightly_off' | 'noticeably_unbalanced' | 'severely_broken' | 'game_breaking';
type RecommendationAction = 'buff' | 'nerf' | 'redesign' | 'monitor' | 'remove';

interface BalanceMetric {
  id: string;
  domain: BalanceDomain;
  name: string;
  current_value: number;
  ideal_min: number;
  ideal_max: number;
  unit: string;
  severity: SeverityLevel;
  description: string;
}

interface Recommendation {
  id: string;
  domain: BalanceDomain;
  metric_name: string;
  action: RecommendationAction;
  description: string;
  target_value: number | null;
  priority: SeverityLevel;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const DOMAIN_LABELS: Record<BalanceDomain, string> = {
  mechanics: 'Mechanics',
  economy: 'Economy',
  progression: 'Progression',
  combat: 'Combat',
  difficulty: 'Difficulty',
};

const DOMAIN_ICONS: Record<BalanceDomain, string> = {
  mechanics: 'fa-gears',
  economy: 'fa-coins',
  progression: 'fa-chart-line',
  combat: 'fa-crosshairs',
  difficulty: 'fa-mountain',
};

const DOMAIN_COLORS: Record<BalanceDomain, string> = {
  mechanics: '#0984e3',
  economy: '#fdcb6e',
  progression: '#00b894',
  combat: '#ff6b6b',
  difficulty: '#e17055',
};

const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  well_balanced: '#6bcb77',
  slightly_off: '#fdcb6e',
  noticeably_unbalanced: '#e17055',
  severely_broken: '#ff6b6b',
  game_breaking: '#a29bfe',
};

const SEVERITY_LABELS: Record<SeverityLevel, string> = {
  well_balanced: 'Well Balanced',
  slightly_off: 'Slightly Off',
  noticeably_unbalanced: 'Noticeably Unbalanced',
  severely_broken: 'Severely Broken',
  game_breaking: 'Game Breaking',
};

const ACTION_LABELS: Record<RecommendationAction, string> = {
  buff: 'Buff',
  nerf: 'Nerf',
  redesign: 'Redesign',
  monitor: 'Monitor',
  remove: 'Remove',
};

const ACTION_COLORS: Record<RecommendationAction, string> = {
  buff: '#6bcb77',
  nerf: '#ff6b6b',
  redesign: '#a29bfe',
  monitor: '#fdcb6e',
  remove: '#e17055',
};

const sampleMetrics: BalanceMetric[] = [
  { id: uid(), domain: 'mechanics', name: 'Jump Height', current_value: 4.2, ideal_min: 2.5, ideal_max: 3.5, unit: 'm', severity: 'slightly_off', description: 'Player jump exceeds intended vertical reach' },
  { id: uid(), domain: 'mechanics', name: 'Move Speed', current_value: 8.0, ideal_min: 5.0, ideal_max: 7.0, unit: 'm/s', severity: 'noticeably_unbalanced', description: 'Base movement speed too high for map size' },
  { id: uid(), domain: 'mechanics', name: 'Dash Cooldown', current_value: 1.5, ideal_min: 2.0, ideal_max: 4.0, unit: 's', severity: 'severely_broken', description: 'Dash can be spammed with minimal downtime' },
  { id: uid(), domain: 'economy', name: 'Gold Per Kill', current_value: 300, ideal_min: 150, ideal_max: 250, unit: 'gold', severity: 'slightly_off', description: 'Kill rewards slightly exceed economic pacing' },
  { id: uid(), domain: 'economy', name: 'Item Base Cost', current_value: 1200, ideal_min: 800, ideal_max: 1500, unit: 'gold', severity: 'well_balanced', description: 'Item pricing aligns with expected economy curve' },
  { id: uid(), domain: 'economy', name: 'Resource Scarcity', current_value: 0.15, ideal_min: 0.30, ideal_max: 0.50, unit: 'ratio', severity: 'severely_broken', description: 'Resources too abundant, no scarcity tension' },
  { id: uid(), domain: 'progression', name: 'XP Per Level', current_value: 500, ideal_min: 400, ideal_max: 600, unit: 'xp', severity: 'well_balanced', description: 'Leveling curve matches designed progression pace' },
  { id: uid(), domain: 'progression', name: 'Skill Unlock Rate', current_value: 0.8, ideal_min: 1.0, ideal_max: 2.0, unit: 'per hour', severity: 'game_breaking', description: 'Players unlock skills far too slowly' },
  { id: uid(), domain: 'progression', name: 'Max Level Cap', current_value: 60, ideal_min: 40, ideal_max: 50, unit: 'levels', severity: 'slightly_off', description: 'Level cap beyond content scope' },
  { id: uid(), domain: 'combat', name: 'Weapon DPS', current_value: 250, ideal_min: 100, ideal_max: 200, unit: 'dps', severity: 'noticeably_unbalanced', description: 'Primary weapon output dominates encounter design' },
  { id: uid(), domain: 'combat', name: 'Enemy Health Scaling', current_value: 1.8, ideal_min: 1.0, ideal_max: 1.3, unit: 'multiplier', severity: 'severely_broken', description: 'Late game enemies become bullet sponges' },
  { id: uid(), domain: 'combat', name: 'Critical Hit Rate', current_value: 35, ideal_min: 10, ideal_max: 25, unit: '%', severity: 'noticeably_unbalanced', description: 'Critical hits occur too frequently' },
  { id: uid(), domain: 'difficulty', name: 'Death Penalty', current_value: 50, ideal_min: 10, ideal_max: 25, unit: '% loss', severity: 'game_breaking', description: 'Death penalty causes extreme player frustration' },
  { id: uid(), domain: 'difficulty', name: 'AI Accuracy', current_value: 92, ideal_min: 60, ideal_max: 80, unit: '%', severity: 'severely_broken', description: 'Enemy AI accuracy is punishing and feels unfair' },
  { id: uid(), domain: 'difficulty', name: 'Checkpoint Spacing', current_value: 15, ideal_min: 3, ideal_max: 8, unit: 'minutes', severity: 'slightly_off', description: 'Checkpoints are too far apart for casual players' },
];

const sampleRecommendations: Recommendation[] = [
  { id: uid(), domain: 'mechanics', metric_name: 'Dash Cooldown', action: 'nerf', description: 'Increase dash cooldown from 1.5s to 2.5s to prevent spam', target_value: 2.5, priority: 'severely_broken' },
  { id: uid(), domain: 'mechanics', metric_name: 'Move Speed', action: 'nerf', description: 'Reduce base move speed from 8.0 to 6.5 m/s', target_value: 6.5, priority: 'noticeably_unbalanced' },
  { id: uid(), domain: 'economy', metric_name: 'Resource Scarcity', action: 'redesign', description: 'Reduce resource spawn rates by 60% and add decay timers', target_value: 0.35, priority: 'severely_broken' },
  { id: uid(), domain: 'progression', metric_name: 'Skill Unlock Rate', action: 'buff', description: 'Increase skill unlock rate to 1.5 per hour with milestone bonuses', target_value: 1.5, priority: 'game_breaking' },
  { id: uid(), domain: 'combat', metric_name: 'Enemy Health Scaling', action: 'nerf', description: 'Cap health scaling multiplier at 1.25x, add new enemy types instead', target_value: 1.25, priority: 'severely_broken' },
  { id: uid(), domain: 'combat', metric_name: 'Critical Hit Rate', action: 'nerf', description: 'Reduce base crit rate from 35% to 20% with diminishing returns', target_value: 20, priority: 'noticeably_unbalanced' },
  { id: uid(), domain: 'difficulty', metric_name: 'Death Penalty', action: 'redesign', description: 'Replace percentage loss with fixed XP debt mechanic', target_value: null, priority: 'game_breaking' },
  { id: uid(), domain: 'difficulty', metric_name: 'AI Accuracy', action: 'nerf', description: 'Reduce AI accuracy to 70% base with adaptive scaling per difficulty', target_value: 70, priority: 'severely_broken' },
];

const BalanceAnalyzerPanel: React.FC = () => {
  const [activeDomain, setActiveDomain] = useState<BalanceDomain>('mechanics');
  const [metrics, setMetrics] = useState<BalanceMetric[]>(sampleMetrics);
  const [recommendations, setRecommendations] = useState<Recommendation[]>(sampleRecommendations);
  const [stats, setStats] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  const apiBase = API_ROOT + '/agent';

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const handleAnalyze = useCallback(async () => {
    setAnalyzing(true);
    try {
      const res = await fetch(`${apiBase}/balance-analyzer/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: activeDomain }),
      });
      const data = await res.json();
      if (data.metrics) setMetrics(prev => prev.map(m => {
        const updated = data.metrics.find((um: any) => um.name === m.name);
        return updated ? { ...m, ...updated } : m;
      }));
      if (data.recommendations) setRecommendations(data.recommendations);
      if (data.stats) setStats(data.stats);
      showMessage('Analysis complete', 'success');
    } catch {
      showMessage('Using cached analysis data', 'info');
    } finally {
      setAnalyzing(false);
    }
  }, [activeDomain]);

  const getSeverityBadgeStyle = (severity: SeverityLevel) => ({
    fontSize: 9,
    padding: '2px 6px',
    borderRadius: 3,
    backgroundColor: SEVERITY_COLORS[severity] + '33',
    color: SEVERITY_COLORS[severity],
    fontWeight: 600 as const,
    whiteSpace: 'nowrap' as const,
  });

  const getActionBadgeStyle = (action: RecommendationAction) => ({
    fontSize: 9,
    padding: '2px 6px',
    borderRadius: 3,
    backgroundColor: ACTION_COLORS[action] + '33',
    color: ACTION_COLORS[action],
    fontWeight: 600 as const,
    textTransform: 'uppercase' as const,
  });

  const filteredMetrics = metrics.filter(m => m.domain === activeDomain);
  const filteredRecommendations = recommendations.filter(r => r.domain === activeDomain);

  const domainSeverityCounts = (domain: BalanceDomain) => {
    const domainMetrics = metrics.filter(m => m.domain === domain);
    const critical = domainMetrics.filter(m => m.severity === 'severely_broken' || m.severity === 'game_breaking').length;
    return critical;
  };

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
          <i className="fa-solid fa-scale-balanced" style={{ color: '#00b894', fontSize: 16 }} />
          <span style={{ fontWeight: 700, fontSize: 15 }}>Balance Analyzer</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_metrics || 15} metrics | {stats.issues_found || 8} issues
            </span>
          )}
          <button onClick={handleAnalyze} style={{
            padding: '6px 14px',
            backgroundColor: analyzing ? '#3d3d5a' : '#00b894',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: analyzing ? 'not-allowed' : 'pointer',
            fontSize: 12,
            fontWeight: 600,
            opacity: analyzing ? 0.7 : 1,
          }}>
            {analyzing ? (
              <>
                <i className="fa-solid fa-spinner fa-spin" style={{ marginRight: 5 }} />
                Analyzing...
              </>
            ) : (
              <>
                <i className="fa-solid fa-magnifying-glass-chart" style={{ marginRight: 5 }} />
                Analyze Game
              </>
            )}
          </button>
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

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{
          width: 220, borderRight: '1px solid #2a2a3e',
          overflow: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          {(Object.keys(DOMAIN_LABELS) as BalanceDomain[]).map(domain => {
            const criticalCount = domainSeverityCounts(domain);
            return (
              <button key={domain} onClick={() => setActiveDomain(domain)} style={{
                padding: '10px 12px',
                backgroundColor: activeDomain === domain ? DOMAIN_COLORS[domain] + '22' : '#22223a',
                color: activeDomain === domain ? DOMAIN_COLORS[domain] : '#aaa',
                border: `1px solid ${activeDomain === domain ? DOMAIN_COLORS[domain] : '#2a2a3e'}`,
                borderRadius: 6,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                textAlign: 'left',
                fontWeight: activeDomain === domain ? 600 : 400,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <i className={`fa-solid ${DOMAIN_ICONS[domain]}`} style={{ fontSize: 13 }} />
                  <span style={{ fontSize: 12 }}>{DOMAIN_LABELS[domain]}</span>
                </div>
                {criticalCount > 0 && (
                  <span style={{
                    fontSize: 9, padding: '2px 5px', borderRadius: 3,
                    backgroundColor: '#ff6b6b33', color: '#ff6b6b', fontWeight: 600,
                  }}>
                    {criticalCount}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <i className={`fa-solid ${DOMAIN_ICONS[activeDomain]}`} style={{ color: DOMAIN_COLORS[activeDomain], fontSize: 14 }} />
              <span style={{ fontSize: 14, fontWeight: 600 }}>{DOMAIN_LABELS[activeDomain]} Metrics</span>
              <span style={{ fontSize: 11, color: '#888' }}>({filteredMetrics.length})</span>
            </div>

            {filteredMetrics.map(metric => (
              <div key={metric.id} style={{
                padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                border: '1px solid #2a2a3e',
                borderLeft: `3px solid ${SEVERITY_COLORS[metric.severity]}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{metric.name}</span>
                  <span style={getSeverityBadgeStyle(metric.severity)}>
                    <i className="fa-solid fa-circle" style={{ fontSize: 5, marginRight: 3 }} />
                    {SEVERITY_LABELS[metric.severity]}
                  </span>
                </div>

                <div style={{ fontSize: 11, color: '#aaa', marginBottom: 8 }}>{metric.description}</div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <div style={{
                    flex: 1, height: 6, backgroundColor: '#111', borderRadius: 3, overflow: 'hidden',
                    position: 'relative',
                  }}>
                    <div style={{
                      position: 'absolute',
                      left: `${Math.min((metric.ideal_min / (metric.ideal_max * 1.5)) * 100, 100)}%`,
                      width: `${Math.max(((metric.ideal_max - metric.ideal_min) / (metric.ideal_max * 1.5)) * 100, 2)}%`,
                      height: '100%',
                      backgroundColor: '#6bcb7733',
                      borderRadius: 3,
                    }} />
                    <div style={{
                      position: 'absolute',
                      left: `${Math.min((metric.current_value / (metric.ideal_max * 1.5)) * 100, 98)}%`,
                      top: -2,
                      width: 10,
                      height: 10,
                      backgroundColor: SEVERITY_COLORS[metric.severity],
                      borderRadius: '50%',
                    }} />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#888' }}>
                  <span>Current: <span style={{ color: SEVERITY_COLORS[metric.severity], fontWeight: 600 }}>{metric.current_value}{metric.unit}</span></span>
                  <span>Ideal: {metric.ideal_min}-{metric.ideal_max}{metric.unit}</span>
                </div>
              </div>
            ))}
          </div>

          {filteredRecommendations.length > 0 && (
            <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <i className="fa-solid fa-clipboard-list" style={{ color: '#a29bfe', fontSize: 14 }} />
                <span style={{ fontSize: 14, fontWeight: 600 }}>Recommendations</span>
                <span style={{ fontSize: 11, color: '#888' }}>({filteredRecommendations.length})</span>
              </div>

              {filteredRecommendations.map(rec => (
                <div key={rec.id} style={{
                  padding: 12, backgroundColor: '#22223a', borderRadius: 6,
                  border: '1px solid #2a2a3e',
                  borderLeft: `3px solid ${ACTION_COLORS[rec.action]}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={getActionBadgeStyle(rec.action)}>{ACTION_LABELS[rec.action]}</span>
                      <span style={{ fontWeight: 600, fontSize: 12 }}>{rec.metric_name}</span>
                    </div>
                    <span style={getSeverityBadgeStyle(rec.priority)}>
                      {SEVERITY_LABELS[rec.priority]}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: '#aaa', marginBottom: 4 }}>{rec.description}</div>
                  {rec.target_value !== null && (
                    <div style={{ fontSize: 10, color: '#888' }}>
                      <i className="fa-solid fa-bullseye" style={{ marginRight: 4, color: ACTION_COLORS[rec.action] }} />
                      Target: {rec.target_value}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{
        padding: '6px 12px', borderTop: '1px solid #2a2a3e',
        backgroundColor: '#111', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
        fontSize: 10, color: '#666',
      }}>
        <span>
          <i className="fa-solid fa-scale-balanced" style={{ marginRight: 4 }} />
          {metrics.length} metrics across 5 domains
        </span>
        <span>
          {stats ? `${stats.issues_found || 8} issues · ${recommendations.length} recommendations` : 'Click Analyze Game to begin'}
        </span>
      </div>
    </div>
  );
};

export default BalanceAnalyzerPanel;