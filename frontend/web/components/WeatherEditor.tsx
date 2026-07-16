import React, { useState, useCallback, useEffect } from 'react';
import { engineApi } from '../utils/api';

interface WeatherZone {
  zone_id: string;
  current_state: string;
  transition_progress: number;
  atmospheric_params: Record<string, number>;
}

const WEATHER_EMOJIS: Record<string, string> = {
  clear: '\u2600\uFE0F',
  cloudy: '\u2601\uFE0F',
  rain: '\U0001F327\uFE0F',
  heavy_rain: '\u26C8\uFE0F',
  storm: '\u26A1',
  snow: '\U0001F328\uFE0F',
  blizzard: '\U0001F32A\uFE0F',
  fog: '\U0001F32B\uFE0F',
  sandstorm: '\U0001F4A8',
  windy: '\U0001F4A8',
};

const STATE_COLORS: Record<string, string> = {
  clear: '#fbbf24',
  cloudy: '#94a3b8',
  rain: '#60a5fa',
  heavy_rain: '#3b82f6',
  storm: '#fbbf24',
  snow: '#e0e7ff',
  blizzard: '#c7d2fe',
  fog: '#9ca3af',
  sandstorm: '#d4a574',
  windy: '#a5b4fc',
};

const WeatherEditor: React.FC = () => {
  const [stats, setStats] = useState<Record<string, any> | null>(null);
  const [selectedZone, setSelectedZone] = useState('');
  const [selectedState, setSelectedState] = useState('clear');
  const [message, setMessage] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const data = await engineApi.weatherStats();
      setStats(data as Record<string, any>);
    } catch {
      setStats({ zones: 0, active_zones: 0 });
    }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const handleSetWeather = async () => {
    if (!selectedZone) return;
    try {
      await engineApi.weatherSet(selectedZone, selectedState);
      setMessage(`Weather set to ${selectedState} in zone ${selectedZone}`);
      loadStats();
    } catch {
      setMessage('Failed to set weather. Check backend.');
    }
  };

  const handleRandomize = async () => {
    if (!selectedZone) return;
    try {
      const data = await engineApi.weatherRandomize(selectedZone);
      setMessage(`Randomized weather in zone ${selectedZone}`);
      loadStats();
    } catch {
      setMessage('Failed to randomize weather.');
    }
  };

  return (
    <div style={{ padding: 16, color: '#e0e0e0', fontFamily: 'monospace', height: '100%', overflow: 'auto' }}>
      <h3 style={{ margin: '0 0 12px', color: '#60a5fa' }}>Weather Editor</h3>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Zones</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.zones || 0}</div>
          </div>
          <div style={{ background: '#1a1a2e', padding: '8px 12px', borderRadius: 6 }}>
            <div style={{ fontSize: 11, color: '#888' }}>Active</div>
            <div style={{ fontSize: 18, fontWeight: 'bold' }}>{stats.active_zones || 0}</div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 12, color: '#aaa', marginBottom: 4 }}>Zone ID</div>
        <input
          value={selectedZone}
          onChange={e => setSelectedZone(e.target.value)}
          placeholder="overworld"
          style={{
            padding: '6px 10px', borderRadius: 6, border: '1px solid #333',
            background: '#1a1a2e', color: '#e0e0e0', fontSize: 12, width: '100%',
            boxSizing: 'border-box',
          }}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 12, color: '#aaa', marginBottom: 6 }}>Weather State</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {Object.keys(WEATHER_EMOJIS).map(state => (
            <button
              key={state}
              onClick={() => setSelectedState(state)}
              style={{
                padding: '6px 12px', borderRadius: 6, fontSize: 13,
                border: selectedState === state ? `2px solid ${STATE_COLORS[state]}` : '1px solid #333',
                background: selectedState === state ? '#1a2a3a' : '#1a1a2e',
                color: selectedState === state ? STATE_COLORS[state] : '#aaa',
                cursor: 'pointer',
              }}
            >
              {WEATHER_EMOJIS[state]} {state.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button onClick={handleSetWeather} style={{
          padding: '8px 16px', borderRadius: 6, border: 'none', background: '#f97316',
          color: '#fff', cursor: 'pointer', fontSize: 12,
        }}>
          Apply Weather
        </button>
        <button onClick={handleRandomize} style={{
          padding: '8px 16px', borderRadius: 6, border: '1px solid #f97316',
          background: 'transparent', color: '#f97316', cursor: 'pointer', fontSize: 12,
        }}>
          Randomize
        </button>
      </div>

      {message && (
        <div style={{ padding: 8, background: '#1a2a1a', borderRadius: 6, color: '#10b981', fontSize: 12 }}>
          {message}
        </div>
      )}
    </div>
  );
};

export default WeatherEditor;