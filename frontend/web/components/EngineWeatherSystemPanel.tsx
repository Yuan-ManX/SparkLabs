"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

const WEATHER_TYPES = ['clear', 'cloudy', 'overcast', 'rain', 'heavy_rain', 'thunderstorm', 'snow', 'blizzard', 'fog', 'heavy_fog', 'windy', 'storm', 'sandstorm', 'heatwave', 'meteor_shower'];
const INTENSITIES = ['light', 'moderate', 'heavy', 'extreme'];

export default function EngineWeatherSystemPanel() {
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<any>({});
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [currentWeather, setCurrentWeather] = useState<any>(null);

  // Weather form
  const [weatherType, setWeatherType] = useState('rain');
  const [weatherIntensity, setWeatherIntensity] = useState('moderate');
  const [weatherDuration, setWeatherDuration] = useState('60');
  const [weatherTransitionTime, setWeatherTransitionTime] = useState('5');

  // Cycle form
  const [deltaSeconds, setDeltaSeconds] = useState('3600');

  // Predict form
  const [forecastSeconds, setForecastSeconds] = useState('86400');

  // Effects
  const [modifiers, setModifiers] = useState<any>(null);

  const fetchStats = useCallback(async () => {
    try { const r = await fetch(`${API_BASE}/weather-system/stats`); if (r.ok) setStats(await r.json()); } catch (e) {}
  }, []);

  const fetchCurrentWeather = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/weather-system/current`);
      if (r.ok) setCurrentWeather(await r.json());
    } catch (e) {}
  }, []);

  const fetchModifiers = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/weather-system/modifiers`);
      if (r.ok) setModifiers(await r.json());
    } catch (e) {}
  }, []);

  useEffect(() => {
    fetchStats();
    fetchCurrentWeather();
    fetchModifiers();
    const i = setInterval(() => { fetchStats(); fetchCurrentWeather(); }, 15000);
    return () => clearInterval(i);
  }, [fetchStats, fetchCurrentWeather, fetchModifiers]);

  const handlePost = async (url: string, body: any) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || data.detail || 'Failed');
      fetchStats();
      fetchCurrentWeather();
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const handleGet = async (url: string) => {
    setLoading(true); setMessage('');
    try {
      const r = await fetch(url);
      const data = await r.json();
      setResult(data);
      setMessage(r.ok ? 'Success' : data.message || 'Failed');
      return data;
    } catch (e: any) { setMessage(e.message); }
    finally { setLoading(false); }
  };

  const setWeather = async () => {
    await handlePost(`${API_BASE}/weather-system/set-weather`, {
      weather_type: weatherType,
      intensity: weatherIntensity,
      duration: parseFloat(weatherDuration),
      transition_time: parseFloat(weatherTransitionTime),
    });
  };

  const transitionWeather = async () => {
    await handlePost(`${API_BASE}/weather-system/transition`, {
      weather_type: weatherType,
      intensity: weatherIntensity,
      duration: parseFloat(weatherDuration),
      transition_time: parseFloat(weatherTransitionTime),
    });
  };

  const advanceTime = async () => {
    await handlePost(`${API_BASE}/weather-system/advance-time`, {
      delta_seconds: parseFloat(deltaSeconds),
    });
  };

  const predictWeather = async () => {
    await handlePost(`${API_BASE}/weather-system/predict`, {
      forecast_seconds: parseInt(forecastSeconds),
    });
  };

  const tabs = ['overview', 'weather', 'cycle', 'effects', 'predict'];

  const inputCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-[#00d4ff] outline-none';
  const selectCls = 'bg-[#1a1a2e] border border-[#2a2a4a] rounded px-3 py-2 text-sm text-white focus:border-[#00d4ff] outline-none';
  const btnPrimary = 'bg-[#00d4ff] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00b8e0] disabled:opacity-50 transition-colors';
  const btnSuccess = 'bg-[#00ff88] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#00e67a] disabled:opacity-50 transition-colors';
  const btnWarning = 'bg-[#fdcb6e] text-black px-4 py-2 rounded text-sm font-medium hover:bg-[#e8b94e] disabled:opacity-50 transition-colors';
  const cardCls = 'bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4';

  const getWeatherColor = (type: string): string => {
    const colors: Record<string, string> = {
      clear: '#f59e0b', cloudy: '#9ca3af', overcast: '#6b7280', rain: '#3b82f6',
      heavy_rain: '#1d4ed8', thunderstorm: '#7c3aed', snow: '#e0f2fe', blizzard: '#bae6fd',
      fog: '#9ca3af', heavy_fog: '#6b7280', windy: '#6ee7b7', storm: '#4f46e5',
      sandstorm: '#d97706', heatwave: '#ef4444', meteor_shower: '#f472b6',
    };
    return colors[type] || '#06b6d4';
  };

  const getWeatherIcon = (type: string): string => {
    const icons: Record<string, string> = {
      clear: '☀️', cloudy: '☁️', overcast: '☁️', rain: '🌧️', heavy_rain: '⛈️',
      thunderstorm: '⚡', snow: '🌨️', blizzard: '❄️', fog: '🌫️', heavy_fog: '🌫️',
      windy: '🌬️', storm: '🌪️', sandstorm: '💨', heatwave: '🔥', meteor_shower: '☄️',
    };
    return icons[type] || '🌈';
  };

  const overviewContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Weather System Overview</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Current Weather', value: stats.current_weather || '--', color: '#00d4ff' },
          { label: 'Current Time', value: stats.current_time || '--', color: '#00ff88' },
          { label: 'Current Season', value: stats.current_season || '--', color: '#fdcb6e' },
          { label: 'Weather Changes', value: stats.weather_changes || 0, color: '#a29bfe' },
        ].map(s => (
          <div key={s.label} className="bg-[#0f0f23] border border-[#2a2a4a] rounded-lg p-4 text-center">
            <div className="text-2xl font-bold capitalize" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-[#999] mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Current Weather Condition Card */}
      {currentWeather && (
        <div className={cardCls}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Current Condition</h3>
          <div className="flex items-center gap-4">
            <span className="text-3xl">{getWeatherIcon(currentWeather.weather_type || 'clear')}</span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium capitalize" style={{ color: getWeatherColor(currentWeather.weather_type) }}>
                  {currentWeather.weather_type?.replace(/_/g, ' ') || 'Clear'}
                </span>
                {currentWeather.intensity && (
                  <span className="px-2 py-0.5 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#ccc] capitalize">
                    {currentWeather.intensity}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {currentWeather.temperature !== undefined && (
                  <div className="text-xs text-[#666]">Temp: <span className="text-[#f59e0b]">{currentWeather.temperature}°</span></div>
                )}
                {currentWeather.humidity !== undefined && (
                  <div className="text-xs text-[#666]">Humidity: <span className="text-[#3b82f6]">{currentWeather.humidity}%</span></div>
                )}
                {currentWeather.wind_speed !== undefined && (
                  <div className="text-xs text-[#666]">Wind: <span className="text-[#6ee7b7]">{currentWeather.wind_speed} m/s</span></div>
                )}
                {currentWeather.visibility !== undefined && (
                  <div className="text-xs text-[#666]">Visibility: <span className="text-[#a29bfe]">{currentWeather.visibility}m</span></div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const weatherContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Weather Control</h2>

      {/* Set Weather */}
      <div className={`${cardCls} mb-4`}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Set Weather</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <select value={weatherType} onChange={e => setWeatherType(e.target.value)} className={selectCls}>
            {WEATHER_TYPES.map(w => <option key={w} value={w} className="bg-[#1a1a2e] capitalize">{w.replace(/_/g, ' ')}</option>)}
          </select>
          <select value={weatherIntensity} onChange={e => setWeatherIntensity(e.target.value)} className={selectCls}>
            {INTENSITIES.map(i => <option key={i} value={i} className="bg-[#1a1a2e] capitalize">{i}</option>)}
          </select>
          <input type="number" placeholder="Duration (s)" value={weatherDuration} onChange={e => setWeatherDuration(e.target.value)} min="1" className={inputCls} />
          <input type="number" placeholder="Transition Time (s)" value={weatherTransitionTime} onChange={e => setWeatherTransitionTime(e.target.value)} min="0" className={inputCls} />
        </div>
        <div className="flex gap-2">
          <button onClick={setWeather} disabled={loading} className={btnPrimary}>
            {loading ? 'Setting...' : 'Set Weather'}
          </button>
          <button onClick={transitionWeather} disabled={loading} className={btnWarning}>
            {loading ? 'Transitioning...' : 'Transition'}
          </button>
        </div>
      </div>

      {/* Weather Types Reference */}
      <div className={cardCls}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Weather Types</h3>
        <div className="flex flex-wrap gap-2">
          {WEATHER_TYPES.map(w => (
            <span key={w} className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs capitalize"
              style={{ color: getWeatherColor(w) }}>
              {getWeatherIcon(w)} {w.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </div>
    </div>
  );

  const cycleContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Day/Night Cycle</h2>

      {/* Advance Time */}
      <div className={`${cardCls} mb-4`}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Advance Time</h3>
        <div className="flex gap-3 items-end">
          <div>
            <span className="text-xs text-[#666] block mb-1">Delta Seconds</span>
            <input type="number" value={deltaSeconds} onChange={e => setDeltaSeconds(e.target.value)} min="1" className={inputCls} />
          </div>
          <button onClick={advanceTime} disabled={loading} className={btnPrimary}>
            {loading ? 'Advancing...' : 'Advance Time'}
          </button>
        </div>
      </div>

      {/* Time Display */}
      {(result || currentWeather) && (
        <div className={cardCls}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Time State</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { label: 'Time of Day', value: (result?.time_of_day || currentWeather?.time_of_day || '--'), color: '#f59e0b', icon: '🕐' },
              { label: 'Ambient Light', value: (result?.ambient_light || currentWeather?.ambient_light || '--'), color: '#fdcb6e', icon: '💡' },
              { label: 'Sky Color', value: (result?.sky_color || currentWeather?.sky_color || '--'), color: '#00d4ff', icon: '🎨' },
            ].map(s => (
              <div key={s.label} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded-lg p-4 text-center">
                <div className="text-lg mb-1">{s.icon}</div>
                <div className="text-sm font-bold capitalize" style={{ color: s.color }}>{s.value}</div>
                <div className="text-xs text-[#666] mt-1">{s.label}</div>
              </div>
            ))}
          </div>
          {result?.day_phase && (
            <div className="mt-3 p-3 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-center">
              <span className="text-xs text-[#666]">Day Phase: </span>
              <span className="text-xs text-[#00ff88] font-medium capitalize">{result.day_phase}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );

  const effectsContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Gameplay Modifiers</h2>

      <div className="flex gap-2 mb-4">
        <button onClick={fetchModifiers} disabled={loading} className={btnPrimary}>
          {loading ? 'Loading...' : 'Refresh Modifiers'}
        </button>
      </div>

      {modifiers && (
        <div className="space-y-4">
          {/* Movement Speed */}
          {modifiers.movement_speed !== undefined && (
            <div className={cardCls}>
              <h3 className="text-sm font-medium text-[#ccc] mb-2">Movement Speed</h3>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-[#1a1a2e] rounded h-2 overflow-hidden">
                  <div className="h-full bg-[#00ff88] rounded transition-all" style={{ width: `${Math.min(modifiers.movement_speed * 100, 100)}%` }} />
                </div>
                <span className="text-xs text-[#00ff88] font-medium">x{modifiers.movement_speed}</span>
              </div>
            </div>
          )}

          {/* Visibility */}
          {modifiers.visibility !== undefined && (
            <div className={cardCls}>
              <h3 className="text-sm font-medium text-[#ccc] mb-2">Visibility</h3>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-[#1a1a2e] rounded h-2 overflow-hidden">
                  <div className="h-full bg-[#00d4ff] rounded transition-all" style={{ width: `${Math.min(modifiers.visibility * 100, 100)}%` }} />
                </div>
                <span className="text-xs text-[#00d4ff] font-medium">x{modifiers.visibility}</span>
              </div>
            </div>
          )}

          {/* Damage */}
          {modifiers.damage !== undefined && (
            <div className={cardCls}>
              <h3 className="text-sm font-medium text-[#ccc] mb-2">Damage Modifier</h3>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-[#1a1a2e] rounded h-2 overflow-hidden">
                  <div className="h-full bg-red-400 rounded transition-all" style={{ width: `${Math.min(modifiers.damage * 100, 100)}%` }} />
                </div>
                <span className="text-xs text-red-400 font-medium">x{modifiers.damage}</span>
              </div>
            </div>
          )}

          {/* Elemental Bonuses */}
          {modifiers.elemental_bonuses && (
            <div className={cardCls}>
              <h3 className="text-sm font-medium text-[#ccc] mb-2">Elemental Bonuses</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(modifiers.elemental_bonuses).map(([k, v]: [string, any]) => (
                  <div key={k} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-2 text-center">
                    <div className="text-xs text-[#fdcb6e] font-bold">x{v}</div>
                    <div className="text-[10px] text-[#666] capitalize">{k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* NPC Behavior */}
          {modifiers.npc_behavior && (
            <div className={cardCls}>
              <h3 className="text-sm font-medium text-[#ccc] mb-2">NPC Behavior</h3>
              <div className="flex flex-wrap gap-2">
                {typeof modifiers.npc_behavior === 'string' ? (
                  <span className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#a29bfe] capitalize">
                    {modifiers.npc_behavior}
                  </span>
                ) : Array.isArray(modifiers.npc_behavior) ? (
                  modifiers.npc_behavior.map((b: any, i: number) => (
                    <span key={i} className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#a29bfe] capitalize">
                      {typeof b === 'string' ? b : b.effect || b.name || `Behavior ${i + 1}`}
                    </span>
                  ))
                ) : (
                  Object.entries(modifiers.npc_behavior).map(([k, v]: [string, any]) => (
                    <span key={k} className="px-2 py-1 bg-[#1a1a2e] border border-[#2a2a4a] rounded text-xs text-[#a29bfe]">
                      {k}: {v}
                    </span>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      )}
      {!modifiers && (
        <p className="text-xs text-[#666] py-4 text-center">Click "Refresh Modifiers" to load gameplay modifiers.</p>
      )}
    </div>
  );

  const predictContent = (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-[#00d4ff]">Weather Prediction</h2>

      <div className={`${cardCls} mb-4`}>
        <h3 className="text-sm font-medium text-[#ccc] mb-3">Forecast</h3>
        <div className="flex gap-3 items-end">
          <div>
            <span className="text-xs text-[#666] block mb-1">Forecast Seconds</span>
            <input type="number" value={forecastSeconds} onChange={e => setForecastSeconds(e.target.value)} min="60" step="3600" className={inputCls} />
          </div>
          <button onClick={predictWeather} disabled={loading} className={btnSuccess}>
            {loading ? 'Predicting...' : 'Predict Weather'}
          </button>
        </div>
      </div>

      {/* Forecast Timeline */}
      {result && result.forecast && Array.isArray(result.forecast) && result.forecast.length > 0 && (
        <div className={cardCls}>
          <h3 className="text-sm font-medium text-[#ccc] mb-3">Forecast Timeline ({result.forecast.length} entries)</h3>
          <div className="space-y-2">
            {result.forecast.map((entry: any, i: number) => (
              <div key={i} className="bg-[#1a1a2e] border border-[#2a2a4a] rounded p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{getWeatherIcon(entry.weather_type || 'clear')}</span>
                    <span className="text-sm font-medium capitalize" style={{ color: getWeatherColor(entry.weather_type) }}>
                      {entry.weather_type?.replace(/_/g, ' ') || 'Clear'}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {entry.intensity && (
                      <span className="px-2 py-0.5 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-[#ccc] capitalize">{entry.intensity}</span>
                    )}
                    {entry.probability !== undefined && (
                      <span className="px-2 py-0.5 bg-[#0f0f23] border border-[#2a2a4a] rounded text-xs text-[#00d4ff]">{Math.round(entry.probability * 100)}%</span>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  {entry.time !== undefined && (
                    <div className="text-[#666]">Time: <span className="text-[#f59e0b]">{entry.time}s</span></div>
                  )}
                  {entry.temperature !== undefined && (
                    <div className="text-[#666]">Temp: <span className="text-[#f59e0b]">{entry.temperature}°</span></div>
                  )}
                  {entry.humidity !== undefined && (
                    <div className="text-[#666]">Humidity: <span className="text-[#3b82f6]">{entry.humidity}%</span></div>
                  )}
                  {entry.wind_speed !== undefined && (
                    <div className="text-[#666]">Wind: <span className="text-[#6ee7b7]">{entry.wind_speed} m/s</span></div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {result && !result.forecast && (
        <pre className="text-xs text-[#999] p-3 bg-[#0f0f23] border border-[#2a2a4a] rounded overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
      )}
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-[#1a1a2e] text-white">
      <div className="flex gap-1 p-3 border-b border-[#2a2a4a] flex-wrap">
        {tabs.map(t => (
          <button key={t} onClick={() => setActiveTab(t)}
            className={`px-3 py-2 rounded text-sm font-medium transition-colors ${activeTab === t ? 'bg-[#00d4ff] text-black' : 'bg-[#0f0f23] text-[#ccc] hover:bg-[#2a2a4a]'}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {message && (
        <div className={`mx-4 mt-2 p-2 rounded text-sm border ${
          message === 'Success' ? 'bg-[#0f0f23] border-[#00ff88]/40 text-[#00ff88]' : 'bg-[#0f0f23] border-[#fdcb6e]/40 text-[#fdcb6e]'
        }`}>{message}</div>
      )}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && overviewContent}
        {activeTab === 'weather' && weatherContent}
        {activeTab === 'cycle' && cycleContent}
        {activeTab === 'effects' && effectsContent}
        {activeTab === 'predict' && predictContent}
      </div>
    </div>
  );
}