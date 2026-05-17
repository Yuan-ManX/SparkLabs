import React, { useState } from 'react';

interface PlayerEvent {
  id: string;
  time: string;
  playerId: string;
  eventType: string;
  details: string;
}

interface RetentionData {
  label: string;
  percentage: number;
  color: string;
}

type EventFilter = 'All' | 'Level Start' | 'Level Complete' | 'Death' | 'Purchase' | 'Achievement' | 'Error';

const EVENT_FILTERS: EventFilter[] = [
  'All',
  'Level Start',
  'Level Complete',
  'Death',
  'Purchase',
  'Achievement',
  'Error',
];

const EVENT_TYPE_COLORS: Record<string, string> = {
  'Level Start': '#22c55e',
  'Level Complete': '#3b82f6',
  Death: '#ef4444',
  Purchase: '#f59e0b',
  Achievement: '#8b5cf6',
  Error: '#ef4444',
};

const MOCK_EVENTS: PlayerEvent[] = [
  { id: '1', time: '2026-05-16 14:32:01', playerId: 'player_04f2', eventType: 'Level Start', details: 'Started Level 12 - Crystal Cavern' },
  { id: '2', time: '2026-05-16 14:30:45', playerId: 'player_1a9c', eventType: 'Purchase', details: 'Purchased Gem Pack x50 ($4.99)' },
  { id: '3', time: '2026-05-16 14:29:18', playerId: 'player_77e3', eventType: 'Death', details: 'Defeated by Boss - Shadow Wyrm (Stage 8)' },
  { id: '4', time: '2026-05-16 14:28:02', playerId: 'player_22b1', eventType: 'Achievement', details: 'Unlocked: Speed Runner (Complete 100 levels)' },
  { id: '5', time: '2026-05-16 14:26:55', playerId: 'player_04f2', eventType: 'Level Complete', details: 'Completed Level 11 with 3 stars' },
  { id: '6', time: '2026-05-16 14:25:33', playerId: 'player_55d8', eventType: 'Error', details: 'Connection timeout on resource download' },
  { id: '7', time: '2026-05-16 14:24:10', playerId: 'player_1a9c', eventType: 'Level Start', details: 'Started Level 7 - Lava Flow' },
  { id: '8', time: '2026-05-16 14:22:47', playerId: 'player_33f6', eventType: 'Death', details: 'Fell into a pit (Stage 15)' },
  { id: '9', time: '2026-05-16 14:21:09', playerId: 'player_77e3', eventType: 'Purchase', details: 'Purchased Weapon Skin - Void Blade ($1.99)' },
  { id: '10', time: '2026-05-16 14:19:52', playerId: 'player_22b1', eventType: 'Achievement', details: 'Unlocked: Persistent Warrior (7-day streak)' },
  { id: '11', time: '2026-05-16 14:18:30', playerId: 'player_99a0', eventType: 'Level Complete', details: 'Completed Level 20 with 2 stars' },
  { id: '12', time: '2026-05-16 14:17:14', playerId: 'player_44c7', eventType: 'Level Start', details: 'Started Level 3 - Tutorial Zone' },
  { id: '13', time: '2026-05-16 14:15:58', playerId: 'player_55d8', eventType: 'Death', details: 'Defeated by enemies in Stage 22' },
  { id: '14', time: '2026-05-16 14:14:22', playerId: 'player_04f2', eventType: 'Purchase', details: 'Purchased XP Booster x3 ($2.99)' },
  { id: '15', time: '2026-05-16 14:12:51', playerId: 'player_33f6', eventType: 'Achievement', details: 'Unlocked: Collector (Collect 1000 coins in one run)' },
];

const SESSION_HOURS = [
  { hour: '00:00', count: 120 },
  { hour: '02:00', count: 85 },
  { hour: '04:00', count: 60 },
  { hour: '06:00', count: 140 },
  { hour: '08:00', count: 310 },
  { hour: '10:00', count: 480 },
  { hour: '12:00', count: 550 },
  { hour: '14:00', count: 620 },
  { hour: '16:00', count: 590 },
  { hour: '18:00', count: 710 },
  { hour: '20:00', count: 810 },
  { hour: '22:00', count: 450 },
];

const RETENTION_DATA: RetentionData[] = [
  { label: 'Day 1', percentage: 100, color: '#22c55e' },
  { label: 'Day 7', percentage: 52, color: '#3b82f6' },
  { label: 'Day 30', percentage: 28, color: '#8b5cf6' },
];

const GameAnalyticsDashboard: React.FC = () => {
  const [eventFilter, setEventFilter] = useState<EventFilter>('All');
  const [dateRange, setDateRange] = useState({ from: '2026-05-09', to: '2026-05-16' });
  const [events] = useState<PlayerEvent[]>(MOCK_EVENTS);
  const [lastRefreshed, setLastRefreshed] = useState(new Date().toLocaleTimeString());

  const maxSessionCount = Math.max(...SESSION_HOURS.map((s) => s.count));

  const filteredEvents =
    eventFilter === 'All'
      ? events
      : events.filter((e) => e.eventType === eventFilter);

  const handleRefresh = () => {
    setLastRefreshed(new Date().toLocaleTimeString());
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h3 style={styles.title}>Game Analytics Dashboard</h3>
          <div style={styles.subtitle}>Last refreshed: {lastRefreshed}</div>
        </div>
        <div style={styles.headerControls}>
          {/* Date range selector */}
          <div style={styles.dateRangeGroup}>
            <label style={styles.dateLabel}>From</label>
            <input
              type="date"
              value={dateRange.from}
              onChange={(e) => setDateRange((prev) => ({ ...prev, from: e.target.value }))}
              style={styles.dateInput}
            />
            <label style={styles.dateLabel}>To</label>
            <input
              type="date"
              value={dateRange.to}
              onChange={(e) => setDateRange((prev) => ({ ...prev, to: e.target.value }))}
              style={styles.dateInput}
            />
          </div>
          {/* Refresh button */}
          <button onClick={handleRefresh} style={styles.refreshButton}>
            <span style={styles.refreshIcon}>&#x21bb;</span> Refresh
          </button>
        </div>
      </div>

      {/* Stat Cards */}
      <div style={styles.statCardsRow}>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>&#x1F465;</div>
          <div>
            <div style={styles.statLabel}>Daily Active Users</div>
            <div style={{ ...styles.statValue, color: '#22c55e' }}>2,847</div>
            <div style={{ ...styles.statChange, color: '#22c55e' }}>&#x2191; 12.4%</div>
          </div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>&#x1F195;</div>
          <div>
            <div style={styles.statLabel}>New Players</div>
            <div style={{ ...styles.statValue, color: '#3b82f6' }}>342</div>
            <div style={{ ...styles.statChange, color: '#22c55e' }}>&#x2191; 8.1%</div>
          </div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>&#x1F3AE;</div>
          <div>
            <div style={styles.statLabel}>Session Count</div>
            <div style={{ ...styles.statValue, color: '#f59e0b' }}>5,612</div>
            <div style={{ ...styles.statChange, color: '#ef4444' }}>&#x2193; 3.2%</div>
          </div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statIcon}>&#x23F1;&#xFE0F;</div>
          <div>
            <div style={styles.statLabel}>Avg Session Duration</div>
            <div style={{ ...styles.statValue, color: '#8b5cf6' }}>24m 38s</div>
            <div style={{ ...styles.statChange, color: '#22c55e' }}>&#x2191; 5.7%</div>
          </div>
        </div>
      </div>

      {/* Charts Row: Session Timeline & Retention Funnel */}
      <div style={styles.chartsRow}>
        {/* Session Timeline */}
        <div style={styles.chartCard}>
          <h4 style={styles.chartTitle}>Session Timeline</h4>
          <div style={styles.barChart}>
            {SESSION_HOURS.map((entry) => {
              const heightPercent = (entry.count / maxSessionCount) * 100;
              return (
                <div key={entry.hour} style={styles.barColumn}>
                  <div style={styles.barValue}>{entry.count}</div>
                  <div style={styles.barTrack}>
                    <div
                      style={{
                        ...styles.barFill,
                        height: `${heightPercent}%`,
                        background:
                          entry.count >= 600
                            ? 'linear-gradient(180deg, #f59e0b, #d97706)'
                            : entry.count >= 300
                              ? 'linear-gradient(180deg, #22c55e, #16a34a)'
                              : 'linear-gradient(180deg, #3b82f6, #2563eb)',
                      }}
                    />
                  </div>
                  <div style={styles.barLabel}>{entry.hour}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Player Retention Funnel */}
        <div style={styles.chartCard}>
          <h4 style={styles.chartTitle}>Player Retention Funnel</h4>
          <div style={styles.retentionContainer}>
            {RETENTION_DATA.map((entry) => (
              <div key={entry.label} style={styles.retentionRow}>
                <div style={styles.retentionLabel}>{entry.label}</div>
                <div style={styles.retentionBarTrack}>
                  <div
                    style={{
                      ...styles.retentionBarFill,
                      width: `${entry.percentage}%`,
                      background: `linear-gradient(90deg, ${entry.color}, ${entry.color}cc)`,
                    }}
                  />
                </div>
                <div style={{ ...styles.retentionPercent, color: entry.color }}>
                  {entry.percentage}%
                </div>
              </div>
            ))}
            <div style={styles.retentionLegend}>
              <span style={styles.legendText}>&#x1F4A1; Day 1 retention baseline — 52% return on Day 7 — 28% still active on Day 30</span>
            </div>
          </div>
        </div>
      </div>

      {/* Event Log */}
      <div style={styles.chartCard}>
        <div style={styles.eventLogHeader}>
          <h4 style={{ ...styles.chartTitle, margin: 0 }}>Event Log</h4>
          <select
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value as EventFilter)}
            style={styles.filterSelect}
          >
            {EVENT_FILTERS.map((filter) => (
              <option key={filter} value={filter}>
                {filter}
              </option>
            ))}
          </select>
        </div>
        <table style={styles.eventTable}>
          <thead>
            <tr>
              <th style={styles.th}>Time</th>
              <th style={styles.th}>Player ID</th>
              <th style={styles.th}>Event Type</th>
              <th style={styles.th}>Details</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.map((event) => (
              <tr key={event.id} style={styles.tr}>
                <td style={styles.td}>{event.time}</td>
                <td style={{ ...styles.td, fontFamily: 'monospace' }}>{event.playerId}</td>
                <td style={styles.td}>
                  <span
                    style={{
                      ...styles.eventBadge,
                      background: `${EVENT_TYPE_COLORS[event.eventType] || '#888'}22`,
                      color: EVENT_TYPE_COLORS[event.eventType] || '#888',
                      borderColor: `${EVENT_TYPE_COLORS[event.eventType] || '#888'}44`,
                    }}
                  >
                    {event.eventType}
                  </span>
                </td>
                <td style={styles.td}>{event.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredEvents.length === 0 && (
          <div style={styles.emptyState}>
            No events match the selected filter.
          </div>
        )}
      </div>
    </div>
  );
};

/* Inline style definitions */
const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: 16,
    color: '#e0e0e0',
    fontFamily: 'monospace',
    height: '100%',
    overflow: 'auto',
    background: '#1e1e2e',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
    flexWrap: 'wrap',
    gap: 12,
  },
  title: {
    margin: 0,
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fbbf24',
  },
  subtitle: {
    fontSize: 11,
    color: '#666',
    marginTop: 4,
  },
  headerControls: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    flexWrap: 'wrap',
  },
  dateRangeGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  dateLabel: {
    fontSize: 11,
    color: '#888',
  },
  dateInput: {
    background: '#2a2a3e',
    border: '1px solid #3a3a4e',
    borderRadius: 4,
    color: '#e0e0e0',
    padding: '4px 8px',
    fontSize: 11,
    fontFamily: 'monospace',
    outline: 'none',
  },
  refreshButton: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '6px 14px',
    background: '#fbbf2422',
    border: '1px solid #fbbf2444',
    borderRadius: 4,
    color: '#fbbf24',
    fontSize: 11,
    fontFamily: 'monospace',
    cursor: 'pointer',
    fontWeight: 'bold',
  },
  refreshIcon: {
    fontSize: 14,
  },
  statCardsRow: {
    display: 'flex',
    gap: 12,
    marginBottom: 16,
    flexWrap: 'wrap',
  },
  statCard: {
    flex: '1 1 180px',
    background: '#2a2a3e',
    padding: '14px 16px',
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    border: '1px solid #3a3a4e',
  },
  statIcon: {
    fontSize: 24,
    width: 40,
    height: 40,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#1e1e2e',
    borderRadius: 8,
  },
  statLabel: {
    fontSize: 11,
    color: '#888',
    marginBottom: 4,
  },
  statValue: {
    fontSize: 22,
    fontWeight: 'bold',
    lineHeight: 1.2,
  },
  statChange: {
    fontSize: 11,
    marginTop: 2,
  },
  chartsRow: {
    display: 'flex',
    gap: 16,
    marginBottom: 16,
    flexWrap: 'wrap',
  },
  chartCard: {
    flex: '1 1 400px',
    background: '#252538',
    borderRadius: 8,
    padding: 16,
    border: '1px solid #3a3a4e',
  },
  chartTitle: {
    margin: '0 0 12px',
    fontSize: 13,
    fontWeight: 'bold',
    color: '#ccc',
  },
  barChart: {
    display: 'flex',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    height: 200,
    gap: 4,
    paddingTop: 20,
  },
  barColumn: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    height: '100%',
    justifyContent: 'flex-end',
  },
  barValue: {
    fontSize: 9,
    color: '#888',
    marginBottom: 4,
    transform: 'rotate(-45deg)',
    transformOrigin: 'center',
    whiteSpace: 'nowrap',
  },
  barTrack: {
    width: '100%',
    maxWidth: 36,
    height: '100%',
    background: '#1e1e2e',
    borderRadius: '4px 4px 0 0',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'flex-end',
    overflow: 'hidden',
  },
  barFill: {
    width: '100%',
    borderRadius: '4px 4px 0 0',
    minHeight: 2,
    transition: 'height 0.3s ease',
  },
  barLabel: {
    fontSize: 9,
    color: '#888',
    marginTop: 6,
    transform: 'rotate(-45deg)',
    transformOrigin: 'center',
  },
  retentionContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  retentionRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  retentionLabel: {
    fontSize: 12,
    color: '#ccc',
    fontWeight: 'bold',
    minWidth: 50,
  },
  retentionBarTrack: {
    flex: 1,
    height: 32,
    background: '#1e1e2e',
    borderRadius: 4,
    overflow: 'hidden',
  },
  retentionBarFill: {
    height: '100%',
    borderRadius: 4,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    paddingRight: 8,
    transition: 'width 0.5s ease',
  },
  retentionPercent: {
    fontSize: 14,
    fontWeight: 'bold',
    minWidth: 40,
  },
  retentionLegend: {
    marginTop: 4,
    paddingTop: 8,
    borderTop: '1px solid #3a3a4e',
  },
  legendText: {
    fontSize: 10,
    color: '#666',
  },
  eventLogHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  filterSelect: {
    background: '#1e1e2e',
    border: '1px solid #3a3a4e',
    borderRadius: 4,
    color: '#e0e0e0',
    padding: '5px 10px',
    fontSize: 11,
    fontFamily: 'monospace',
    outline: 'none',
    cursor: 'pointer',
  },
  eventTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: 11,
  },
  th: {
    textAlign: 'left',
    padding: '8px 10px',
    borderBottom: '1px solid #3a3a4e',
    color: '#888',
    fontSize: 10,
    fontWeight: 'bold',
    textTransform: 'uppercase' as React.CSSProperties['textTransform'],
  },
  tr: {
    borderBottom: '1px solid #2a2a3e',
  },
  td: {
    padding: '8px 10px',
    color: '#ccc',
  },
  eventBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: 3,
    fontSize: 10,
    fontWeight: 'bold',
    border: '1px solid',
  },
  emptyState: {
    textAlign: 'center',
    padding: 24,
    color: '#666',
    fontSize: 12,
  },
};

export default GameAnalyticsDashboard;