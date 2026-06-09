import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000/api/engine';

interface WeatherStats {
  active_weathers: number;
  particle_count: number;
  transition_count: number;
}

interface WeatherState {
  region_id: string;
  weather_type: string;
  intensity: number;
  temperature: number;
  humidity: number;
  wind_speed: number;
  particle_count: number;
}

interface WeatherRegion {
  id: string;
  name: string;
  climate_zone: string;
  current_weather: string;
}

type TabId = 'overview' | 'control' | 'regions';

const WEATHER_TYPES = [
  'clear', 'cloudy', 'rain', 'heavy_rain', 'snow',
  'blizzard', 'fog', 'thunderstorm', 'sandstorm',
  'windy', 'heat_wave', 'hail', 'drizzle',
];

const CLIMATE_ZONES = [
  'tropical', 'subtropical', 'temperate', 'continental',
  'polar', 'arid', 'mediterranean', 'oceanic',
];

export default function WeatherSystemPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<WeatherStats | null>(null);
  const [weathers, setWeathers] = useState<WeatherState[]>([]);
  const [regions, setRegions] = useState<WeatherRegion[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  // Weather control form
  const [selectedRegion, setSelectedRegion] = useState('');
  const [weatherType, setWeatherType] = useState('rain');
  const [intensity, setIntensity] = useState(50);
  const [transitionDuration, setTransitionDuration] = useState('3000');

  // Climate assignment
  const [climateRegion, setClimateRegion] = useState('');
  const [climateZone, setClimateZone] = useState('temperate');

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/weather-system/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchWeathers = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/weather-system/current`);
      const data = await res.json();
      if (data.weathers) setWeathers(data.weathers);
    } catch {}
  }, []);

  const fetchRegions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/weather-system/regions`);
      const data = await res.json();
      if (data.regions) {
        setRegions(data.regions);
        if (!selectedRegion && data.regions.length > 0) {
          setSelectedRegion(data.regions[0].id);
          setClimateRegion(data.regions[0].id);
        }
      }
    } catch {}
  }, [selectedRegion]);

  useEffect(() => {
    fetchStats();
    fetchWeathers();
    fetchRegions();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchWeathers, fetchRegions]);

  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), 3000);
  };

  const handleSetWeather = async () => {
    if (!selectedRegion) { showMessage('Select a region'); return; }
    try {
      const res = await fetch(`${API_BASE}/weather-system/set`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          region_id: selectedRegion,
          weather_type: weatherType,
          intensity: intensity / 100,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Weather set to ${weatherType} (${intensity}%)`);
        fetchWeathers();
        fetchStats();
      }
    } catch {
      showMessage('Failed to set weather');
    }
  };

  const handleSmoothTransition = async () => {
    if (!selectedRegion) { showMessage('Select a region'); return; }
    try {
      const res = await fetch(`${API_BASE}/weather-system/transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          region_id: selectedRegion,
          weather_type: weatherType,
          intensity: intensity / 100,
          duration_ms: parseInt(transitionDuration),
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Transitioning to ${weatherType} over ${transitionDuration}ms`);
        fetchWeathers();
      }
    } catch {
      showMessage('Failed to start transition');
    }
  };

  const handleAssignClimate = async () => {
    if (!climateRegion) { showMessage('Select a region'); return; }
    try {
      const res = await fetch(`${API_BASE}/weather-system/climate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          region_id: climateRegion,
          climate_zone: climateZone,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(data.error);
      } else {
        showMessage(`Climate zone set to ${climateZone}`);
        fetchRegions();
      }
    } catch {
      showMessage('Failed to assign climate');
    }
  };

  const getWeatherIcon = (type: string): string => {
    const icons: Record<string, string> = {
      clear: '☀️', cloudy: '☁️', rain: '🌧️', heavy_rain: '⛈️',
      snow: '🌨️', blizzard: '❄️', fog: '🌫️', thunderstorm: '⚡',
      sandstorm: '💨', windy: '🌬️', heat_wave: '🔥', hail: '🌨️', drizzle: '🌦️',
    };
    return icons[type] || '🌈';
  };

  const getWeatherColor = (type: string): string => {
    const colors: Record<string, string> = {
      clear: '#f59e0b', cloudy: '#9ca3af', rain: '#3b82f6',
      heavy_rain: '#1d4ed8', snow: '#e0f2fe', blizzard: '#bae6fd',
      fog: '#9ca3af', thunderstorm: '#7c3aed', sandstorm: '#d97706',
      windy: '#6ee7b7', heat_wave: '#ef4444', hail: '#06b6d4', drizzle: '#93c5fd',
    };
    return colors[type] || '#06b6d4';
  };

  if (loading) {
    return (
      <div style={{ padding: 24, color: '#a0a0b0' }}>
        Loading Weather System...
      </div>
    );
  }

  return (
    <div style={{ padding: 24, color: '#e0e0e0' }}>
      <h2 style={{ margin: '0 0 8px 0', fontSize: 20, color: '#fff' }}>
        Weather System
      </h2>
      <p style={{ margin: '0 0 16px 0', fontSize: 12, color: '#888' }}>
        Control and simulate dynamic weather systems across game regions
      </p>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #333' }}>
        {[
          { id: 'overview' as TabId, label: 'Overview' },
          { id: 'control' as TabId, label: 'Control' },
          { id: 'regions' as TabId, label: 'Regions' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 16px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid #06b6d4' : '2px solid transparent',
              color: activeTab === tab.id ? '#06b6d4' : '#888',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: activeTab === tab.id ? 600 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div style={{
          padding: '8px 12px',
          background: '#1a1a2e',
          border: '1px solid #06b6d4',
          borderRadius: 6,
          marginBottom: 12,
          fontSize: 12,
          color: '#67e8f9',
        }}>
          {message}
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div>
          {stats ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              <StatCard label="Active Weathers" value={String(stats.active_weathers)} accent="#06b6d4" />
              <StatCard label="Particle Count" value={stats.particle_count.toLocaleString()} accent="#06b6d4" />
              <StatCard label="Transitions" value={String(stats.transition_count)} accent="#06b6d4" />
            </div>
          ) : (
            <p style={{ color: '#888' }}>No statistics available</p>
          )}

          {/* Current Weather Display */}
          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Current Weather</h3>
          {weathers.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {weathers.map((w) => (
                <div key={w.region_id} style={{
                  padding: '12px 16px',
                  background: '#1a1a2e',
                  borderRadius: 8,
                  border: `1px solid ${getWeatherColor(w.weather_type)}33`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span style={{ fontSize: 24 }}>{getWeatherIcon(w.weather_type)}</span>
                    <div>
                      <div style={{ fontSize: 13, color: getWeatherColor(w.weather_type), fontWeight: 600 }}>
                        {w.weather_type.replace('_', ' ')}
                      </div>
                      <div style={{ fontSize: 11, color: '#666' }}>{w.region_id}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 20, fontSize: 11, color: '#888' }}>
                    <div>
                      <div style={{ color: '#555', marginBottom: 2 }}>Intensity</div>
                      <div style={{ color: '#06b6d4' }}>{(w.intensity * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                      <div style={{ color: '#555', marginBottom: 2 }}>Temp</div>
                      <div style={{ color: '#f59e0b' }}>{w.temperature}°</div>
                    </div>
                    <div>
                      <div style={{ color: '#555', marginBottom: 2 }}>Humidity</div>
                      <div style={{ color: '#3b82f6' }}>{(w.humidity * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                      <div style={{ color: '#555', marginBottom: 2 }}>Wind</div>
                      <div style={{ color: '#6ee7b7' }}>{w.wind_speed} m/s</div>
                    </div>
                    <div>
                      <div style={{ color: '#555', marginBottom: 2 }}>Particles</div>
                      <div style={{ color: '#a78bfa' }}>{w.particle_count.toLocaleString()}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No active weather data</p>
          )}
        </div>
      )}

      {/* Control Tab */}
      {activeTab === 'control' && (
        <div>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>Weather Control</h3>

          {/* Region Selector */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: '#888' }}>Region:</label>
            <select value={selectedRegion} onChange={(e) => setSelectedRegion(e.target.value)} style={selectStyle}>
              <option value="">Select region</option>
              {regions.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          {/* Weather Type Selector */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: '#888' }}>Weather:</label>
            <select value={weatherType} onChange={(e) => setWeatherType(e.target.value)} style={selectStyle}>
              {WEATHER_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace('_', ' ')}</option>
              ))}
            </select>
          </div>

          {/* Intensity Slider */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, color: '#888', display: 'block', marginBottom: 6 }}>
              Intensity: <span style={{ color: '#06b6d4' }}>{intensity}%</span>
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={intensity}
              onChange={(e) => setIntensity(parseInt(e.target.value))}
              style={{
                width: '100%',
                maxWidth: 300,
                accentColor: '#06b6d4',
                background: '#0f0f23',
              }}
            />
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
            <button onClick={handleSetWeather} style={buttonStyle('#06b6d4')}>
              Set Weather
            </button>
          </div>

          {/* Smooth Transition */}
          <h3 style={{ margin: '20px 0 12px', fontSize: 14, color: '#ccc' }}>Smooth Transition</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: '#888' }}>Duration:</label>
            <input
              type="number"
              value={transitionDuration}
              onChange={(e) => setTransitionDuration(e.target.value)}
              style={{ ...inputStyle, width: 80 }}
              min="100"
              step="100"
            />
            <span style={{ fontSize: 11, color: '#666' }}>ms</span>
          </div>
          <button onClick={handleSmoothTransition} style={buttonStyle('#0891b2')}>
            Smooth Transition
          </button>

          {/* Climate Assignment */}
          <h3 style={{ margin: '24px 0 12px', fontSize: 14, color: '#ccc' }}>Climate Zone Assignment</h3>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <select value={climateRegion} onChange={(e) => setClimateRegion(e.target.value)} style={selectStyle}>
              <option value="">Select region</option>
              {regions.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
            <select value={climateZone} onChange={(e) => setClimateZone(e.target.value)} style={selectStyle}>
              {CLIMATE_ZONES.map((z) => (
                <option key={z} value={z}>{z}</option>
              ))}
            </select>
            <button onClick={handleAssignClimate} style={buttonStyle('#06b6d4')}>
              Assign
            </button>
          </div>
        </div>
      )}

      {/* Regions Tab */}
      {activeTab === 'regions' && (
        <div>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, color: '#ccc' }}>
            Weather Regions ({regions.length})
          </h3>
          {regions.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {regions.map((region) => (
                <div key={region.id} style={{
                  padding: '10px 14px',
                  background: '#1a1a2e',
                  borderRadius: 6,
                  fontSize: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span style={{ color: '#06b6d4', fontFamily: 'monospace' }}>{region.name}</span>
                    <span style={{
                      padding: '2px 8px',
                      background: '#2a2a3e',
                      borderRadius: 3,
                      fontSize: 10,
                      color: '#aaa',
                    }}>{region.climate_zone}</span>
                  </div>
                  <span style={{
                    padding: '2px 10px',
                    background: getWeatherColor(region.current_weather) + '22',
                    border: `1px solid ${getWeatherColor(region.current_weather)}44`,
                    borderRadius: 3,
                    fontSize: 10,
                    color: getWeatherColor(region.current_weather),
                  }}>
                    {region.current_weather.replace('_', ' ')}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: 12 }}>No regions available</p>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{
      padding: '14px 16px',
      background: '#1a1a2e',
      borderRadius: 8,
      border: '1px solid #2a2a3e',
    }}>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 600, color: accent }}>{value}</div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '6px 10px',
  background: '#0f0f23',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#e0e0e0',
  fontSize: 12,
  width: 140,
};

const selectStyle: React.CSSProperties = {
  padding: '6px 10px',
  background: '#0f0f23',
  border: '1px solid #333',
  borderRadius: 4,
  color: '#e0e0e0',
  fontSize: 12,
};

const buttonStyle = (accent: string): React.CSSProperties => ({
  padding: '6px 14px',
  background: accent,
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 500,
});