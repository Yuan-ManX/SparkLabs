"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE as API_ROOT } from '../utils/api';

const API_BASE = API_ROOT + '/engine';

type TabId = 'overview' | 'generate-city' | 'cities' | 'districts' | 'buildings' | 'roads' | 'analyze';

interface Stats {
  total_cities: number;
  total_roads: number;
  total_districts: number;
  total_buildings: number;
  total_landmarks: number;
}

interface City {
  city_id: string;
  name: string;
  style: string;
  config: Record<string, any>;
}

interface District {
  district_id: string;
  city_id: string;
  name: string;
  type: string;
  area: number;
  population_density: number;
}

interface Building {
  building_id: string;
  city_id: string;
  district_id: string;
  type: string;
  height: number;
  area: number;
  purpose: string;
}

interface Road {
  road_id: string;
  city_id: string;
  name: string;
  type: string;
  length: number;
  connects: string[];
}

interface CityAnalysis {
  city_id: string;
  total_area: number;
  building_count: number;
  road_network_length: number;
  landmark_count: number;
  density_score: number;
  walkability: number;
  green_space_ratio: number;
}

const uid = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function EngineProceduralCityPanel() {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [stats, setStats] = useState<Stats | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Generate City form
  const [generateForm, setGenerateForm] = useState({
    name: '',
    style: 'modern',
    config: '',
  });
  const [generateLoading, setGenerateLoading] = useState(false);
  const [city, setCity] = useState<City | null>(null);

  // Cities list
  const [citiesLoading, setCitiesLoading] = useState(false);
  const [cities, setCities] = useState<City[] | null>(null);

  // Districts form
  const [districtsForm, setDistrictsForm] = useState({
    city_id: '',
    num_districts: '4',
  });
  const [districtsLoading, setDistrictsLoading] = useState(false);
  const [districts, setDistricts] = useState<District[] | null>(null);

  // Buildings form
  const [buildingsForm, setBuildingsForm] = useState({
    city_id: '',
    district_id: '',
    num_buildings: '10',
  });
  const [buildingsLoading, setBuildingsLoading] = useState(false);
  const [buildings, setBuildings] = useState<Building[] | null>(null);

  // Roads
  const [roadsCityId, setRoadsCityId] = useState('');
  const [roadsLoading, setRoadsLoading] = useState(false);
  const [roads, setRoads] = useState<Road[] | null>(null);

  // Analyze
  const [analyzeCityId, setAnalyzeCityId] = useState('');
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [analysis, setAnalysis] = useState<CityAnalysis | null>(null);

  // District detail
  const [districtDetailCityId, setDistrictDetailCityId] = useState('');
  const [districtDetailDistrictId, setDistrictDetailDistrictId] = useState('');
  const [districtDetailLoading, setDistrictDetailLoading] = useState(false);
  const [districtDetail, setDistrictDetail] = useState<District | null>(null);

  // Buildings by district
  const [buildingsByDistrictCityId, setBuildingsByDistrictCityId] = useState('');
  const [buildingsByDistrictDistrictId, setBuildingsByDistrictDistrictId] = useState('');
  const [buildingsByDistrictLoading, setBuildingsByDistrictLoading] = useState(false);
  const [buildingsByDistrict, setBuildingsByDistrict] = useState<Building[] | null>(null);

  const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/procedural-city/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data.stats || data);
      }
    } catch { /* use defaults */ }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // --- Generate City ---
  const handleGenerateCity = async () => {
    if (!generateForm.name.trim()) {
      showMessage('City name is required', 'error');
      return;
    }
    setGenerateLoading(true);
    try {
      let configObj: Record<string, any> = {};
      if (generateForm.config.trim()) {
        try { configObj = JSON.parse(generateForm.config); } catch { /* ignore */ }
      }
      const body = {
        name: generateForm.name,
        style: generateForm.style,
        config: configObj,
      };
      const res = await fetch(`${API_BASE}/procedural-city/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setCity(data.city || data);
        showMessage('City generated successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to generate city', 'error');
      }
    } catch {
      setCity({
        city_id: uid(),
        name: generateForm.name,
        style: generateForm.style,
        config: {},
      });
      showMessage('City generated (offline mode)', 'info');
    } finally {
      setGenerateLoading(false);
    }
  };

  // --- Fetch Cities ---
  const handleFetchCities = async () => {
    setCitiesLoading(true);
    try {
      const res = await fetch(`${API_BASE}/procedural-city/cities`);
      const data = await res.json();
      if (res.ok) {
        setCities(data.cities || data);
        showMessage('Cities loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load cities', 'error');
      }
    } catch {
      setCities([
        { city_id: uid(), name: 'Neo Tokyo', style: 'cyberpunk', config: {} },
        { city_id: uid(), name: 'Old Haven', style: 'medieval', config: {} },
        { city_id: uid(), name: 'Solaris Bay', style: 'modern', config: {} },
      ]);
      showMessage('Cities loaded (offline mode)', 'info');
    } finally {
      setCitiesLoading(false);
    }
  };

  // --- Generate Districts ---
  const handleGenerateDistricts = async () => {
    if (!districtsForm.city_id.trim()) {
      showMessage('City ID is required', 'error');
      return;
    }
    setDistrictsLoading(true);
    try {
      const body = {
        city_id: districtsForm.city_id,
        num_districts: parseInt(districtsForm.num_districts) || 4,
      };
      const res = await fetch(`${API_BASE}/procedural-city/generate-districts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setDistricts(data.districts || data);
        showMessage('Districts generated successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to generate districts', 'error');
      }
    } catch {
      setDistricts([
        { district_id: uid(), city_id: districtsForm.city_id, name: 'Downtown', type: 'commercial', area: 250, population_density: 0.8 },
        { district_id: uid(), city_id: districtsForm.city_id, name: 'Suburbs', type: 'residential', area: 500, population_density: 0.5 },
        { district_id: uid(), city_id: districtsForm.city_id, name: 'Industrial Park', type: 'industrial', area: 300, population_density: 0.2 },
        { district_id: uid(), city_id: districtsForm.city_id, name: 'Green Belt', type: 'park', area: 150, population_density: 0.1 },
      ]);
      showMessage('Districts generated (offline mode)', 'info');
    } finally {
      setDistrictsLoading(false);
    }
  };

  // --- Generate Buildings ---
  const handleGenerateBuildings = async () => {
    if (!buildingsForm.city_id.trim() || !buildingsForm.district_id.trim()) {
      showMessage('City ID and District ID are required', 'error');
      return;
    }
    setBuildingsLoading(true);
    try {
      const body = {
        city_id: buildingsForm.city_id,
        district_id: buildingsForm.district_id,
        num_buildings: parseInt(buildingsForm.num_buildings) || 10,
      };
      const res = await fetch(`${API_BASE}/procedural-city/generate-buildings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.ok) {
        setBuildings(data.buildings || data);
        showMessage('Buildings generated successfully', 'success');
        fetchStats();
      } else {
        showMessage(data.error || 'Failed to generate buildings', 'error');
      }
    } catch {
      setBuildings([
        { building_id: uid(), city_id: buildingsForm.city_id, district_id: buildingsForm.district_id, type: 'skyscraper', height: 120, area: 2000, purpose: 'office' },
        { building_id: uid(), city_id: buildingsForm.city_id, district_id: buildingsForm.district_id, type: 'apartment', height: 45, area: 800, purpose: 'residential' },
        { building_id: uid(), city_id: buildingsForm.city_id, district_id: buildingsForm.district_id, type: 'warehouse', height: 15, area: 3000, purpose: 'industrial' },
      ]);
      showMessage('Buildings generated (offline mode)', 'info');
    } finally {
      setBuildingsLoading(false);
    }
  };

  // --- Fetch Roads ---
  const handleFetchRoads = async () => {
    if (!roadsCityId.trim()) {
      showMessage('City ID is required', 'error');
      return;
    }
    setRoadsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/procedural-city/roads?city_id=${encodeURIComponent(roadsCityId)}`);
      const data = await res.json();
      if (res.ok) {
        setRoads(data.roads || data);
        showMessage('Roads loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load roads', 'error');
      }
    } catch {
      setRoads([
        { road_id: uid(), city_id: roadsCityId, name: 'Main Street', type: 'avenue', length: 2500, connects: ['downtown', 'suburbs'] },
        { road_id: uid(), city_id: roadsCityId, name: 'Industrial Blvd', type: 'highway', length: 5000, connects: ['downtown', 'industrial_park'] },
        { road_id: uid(), city_id: roadsCityId, name: 'Park Way', type: 'boulevard', length: 1200, connects: ['suburbs', 'green_belt'] },
      ]);
      showMessage('Roads loaded (offline mode)', 'info');
    } finally {
      setRoadsLoading(false);
    }
  };

  // --- Fetch Analysis ---
  const handleFetchAnalysis = async () => {
    if (!analyzeCityId.trim()) {
      showMessage('City ID is required', 'error');
      return;
    }
    setAnalyzeLoading(true);
    try {
      const res = await fetch(`${API_BASE}/procedural-city/analyze?city_id=${encodeURIComponent(analyzeCityId)}`);
      const data = await res.json();
      if (res.ok) {
        setAnalysis(data.analysis || data);
        showMessage('Analysis loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load analysis', 'error');
      }
    } catch {
      setAnalysis({
        city_id: analyzeCityId,
        total_area: 2500,
        building_count: 42,
        road_network_length: 8700,
        landmark_count: 5,
        density_score: 0.65,
        walkability: 0.72,
        green_space_ratio: 0.15,
      });
      showMessage('Analysis loaded (offline mode)', 'info');
    } finally {
      setAnalyzeLoading(false);
    }
  };

  // --- Fetch District Detail ---
  const handleFetchDistrictDetail = async () => {
    if (!districtDetailCityId.trim() || !districtDetailDistrictId.trim()) {
      showMessage('City ID and District ID are required', 'error');
      return;
    }
    setDistrictDetailLoading(true);
    try {
      const res = await fetch(`${API_BASE}/procedural-city/district?city_id=${encodeURIComponent(districtDetailCityId)}&district_id=${encodeURIComponent(districtDetailDistrictId)}`);
      const data = await res.json();
      if (res.ok) {
        setDistrictDetail(data.district || data);
        showMessage('District detail loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load district', 'error');
      }
    } catch {
      setDistrictDetail({
        district_id: districtDetailDistrictId,
        city_id: districtDetailCityId,
        name: 'Downtown Core',
        type: 'commercial',
        area: 250,
        population_density: 0.85,
      });
      showMessage('District detail loaded (offline mode)', 'info');
    } finally {
      setDistrictDetailLoading(false);
    }
  };

  // --- Fetch Buildings by District ---
  const handleFetchBuildingsByDistrict = async () => {
    if (!buildingsByDistrictCityId.trim() || !buildingsByDistrictDistrictId.trim()) {
      showMessage('City ID and District ID are required', 'error');
      return;
    }
    setBuildingsByDistrictLoading(true);
    try {
      const res = await fetch(`${API_BASE}/procedural-city/buildings?city_id=${encodeURIComponent(buildingsByDistrictCityId)}&district_id=${encodeURIComponent(buildingsByDistrictDistrictId)}`);
      const data = await res.json();
      if (res.ok) {
        setBuildingsByDistrict(data.buildings || data);
        showMessage('Buildings loaded', 'success');
      } else {
        showMessage(data.error || 'Failed to load buildings', 'error');
      }
    } catch {
      setBuildingsByDistrict([
        { building_id: uid(), city_id: buildingsByDistrictCityId, district_id: buildingsByDistrictDistrictId, type: 'skyscraper', height: 150, area: 2500, purpose: 'office' },
        { building_id: uid(), city_id: buildingsByDistrictCityId, district_id: buildingsByDistrictDistrictId, type: 'mall', height: 20, area: 5000, purpose: 'commercial' },
      ]);
      showMessage('Buildings loaded (offline mode)', 'info');
    } finally {
      setBuildingsByDistrictLoading(false);
    }
  };

  const tabItems: { key: TabId; label: string; icon: string }[] = [
    { key: 'overview', label: 'Overview', icon: '\uD83C\uDF06' },
    { key: 'generate-city', label: 'Generate City', icon: '\uD83C\uDFD7\uFE0F' },
    { key: 'cities', label: 'Cities', icon: '\uD83C\uDFD9\uFE0F' },
    { key: 'districts', label: 'Districts', icon: '\uD83D\uDDFA\uFE0F' },
    { key: 'buildings', label: 'Buildings', icon: '\uD83C\uDFE2' },
    { key: 'roads', label: 'Roads', icon: '\uD83D\uDEE3\uFE0F' },
    { key: 'analyze', label: 'Analyze', icon: '\uD83D\uDCCA' },
  ];

  const darkInputStyle: React.CSSProperties = {
    width: '100%', padding: '6px 10px', fontSize: 12,
    backgroundColor: '#111', color: '#ccc',
    border: '1px solid #333', borderRadius: 4, boxSizing: 'border-box', outline: 'none',
  };

  const darkTextareaStyle: React.CSSProperties = {
    ...darkInputStyle, resize: 'vertical', fontFamily: 'monospace',
  };

  const darkSelectStyle: React.CSSProperties = {
    ...darkInputStyle, cursor: 'pointer',
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

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      backgroundColor: '#1a1a2e', color: '#e0e0e0',
      fontFamily: 'monospace', fontSize: 13, padding: '20px',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #2a2a3e',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>{'\uD83C\uDF06'}</span>
          <span style={{ fontWeight: 700, fontSize: 15 }}>Procedural City</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {stats && (
            <span style={{ fontSize: 10, color: '#888' }}>
              {stats.total_cities ?? 0} cities · {stats.total_buildings ?? 0} buildings
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
      <div style={{ display: 'flex', borderBottom: '1px solid #2a2a3e', flexWrap: 'wrap' }}>
        {tabItems.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 12px', fontSize: 11, fontWeight: 600,
              backgroundColor: activeTab === tab.key ? '#16213e' : 'transparent',
              color: activeTab === tab.key ? '#e0e0e0' : '#888',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #00d4ff' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>

        {/* Tab: Overview */}
        {activeTab === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 12, color: '#aaa' }}>
                {'\uD83C\uDF06'} Procedural City Status
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Total Cities</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#00d4ff' }}>{stats?.total_cities ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Districts</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#6bcb77' }}>{stats?.total_districts ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Buildings</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#fdcb6e' }}>{stats?.total_buildings ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Roads</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#ff6b6b' }}>{stats?.total_roads ?? 0}</span>
                </div>
                <div style={{
                  padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                }}>
                  <span style={{ fontSize: 10, color: '#888' }}>Landmarks</span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#a29bfe' }}>{stats?.total_landmarks ?? 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Generate City */}
        {activeTab === 'generate-city' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83C\uDFD7\uFE0F'} Generate New City
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div>
                  <span style={labelStyle}>City Name *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. Neo Tokyo"
                    value={generateForm.name}
                    onChange={e => setGenerateForm(prev => ({ ...prev, name: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>Style</span>
                    <select
                      style={darkSelectStyle}
                      value={generateForm.style}
                      onChange={e => setGenerateForm(prev => ({ ...prev, style: e.target.value }))}
                    >
                      <option value="modern">Modern</option>
                      <option value="cyberpunk">Cyberpunk</option>
                      <option value="medieval">Medieval</option>
                      <option value="industrial">Industrial</option>
                      <option value="futuristic">Futuristic</option>
                      <option value="colonial">Colonial</option>
                      <option value="art_deco">Art Deco</option>
                      <option value="brutalist">Brutalist</option>
                    </select>
                  </div>
                  <div>
                    <span style={labelStyle}>Config (JSON)</span>
                    <textarea
                      style={{ ...darkTextareaStyle, height: 36 }}
                      placeholder='{"grid_size": 100, "seed": 42}'
                      value={generateForm.config}
                      onChange={e => setGenerateForm(prev => ({ ...prev, config: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleGenerateCity}
                disabled={generateLoading}
                style={generateLoading ? disabledBtnStyle('#00d4ff') : primaryBtnStyle('#00d4ff')}
              >
                {generateLoading ? 'Generating...' : '\uD83C\uDFD7\uFE0F Generate City'}
              </button>
            </div>

            {city && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Generated City
                </div>
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{city.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#1e1e1e', color: '#00d4ff', fontWeight: 600,
                    }}>
                      {city.style}
                    </span>
                  </div>
                  <div style={{ fontSize: 9, color: '#666' }}>
                    ID: <span style={{ color: '#888' }}>{city.city_id}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Cities */}
        {activeTab === 'cities' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#6bcb77' }}>
                {'\uD83C\uDFD9\uFE0F'} All Cities
              </div>
              <button
                onClick={handleFetchCities}
                disabled={citiesLoading}
                style={{
                  ...(citiesLoading ? disabledBtnStyle('#6bcb77') : primaryBtnStyle('#6bcb77')),
                  width: '100%', marginBottom: 10,
                }}
              >
                {citiesLoading ? 'Loading...' : '\uD83D\uDD04 Fetch Cities'}
              </button>

              {cities && cities.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {cities.map(c => (
                    <div key={c.city_id} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #6bcb77',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{c.name}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: '#1e1e1e', color: '#00d4ff', fontWeight: 600,
                        }}>
                          {c.style}
                        </span>
                      </div>
                      <div style={{ fontSize: 9, color: '#888', marginTop: 2 }}>
                        ID: {c.city_id}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Districts */}
        {activeTab === 'districts' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#fdcb6e' }}>
                {'\uD83D\uDDFA\uFE0F'} Generate Districts
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>City ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. city_xxx"
                      value={districtsForm.city_id}
                      onChange={e => setDistrictsForm(prev => ({ ...prev, city_id: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>Number of Districts</span>
                    <input
                      style={darkInputStyle}
                      placeholder="4"
                      value={districtsForm.num_districts}
                      onChange={e => setDistrictsForm(prev => ({ ...prev, num_districts: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleGenerateDistricts}
                disabled={districtsLoading}
                style={districtsLoading ? disabledBtnStyle('#fdcb6e') : primaryBtnStyle('#fdcb6e')}
              >
                {districtsLoading ? 'Generating...' : '\uD83D\uDDFA\uFE0F Generate Districts'}
              </button>
            </div>

            {districts && districts.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Generated Districts
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {districts.map(d => (
                    <div key={d.district_id} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #fdcb6e',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                        <span style={{ fontWeight: 600, fontSize: 12 }}>{d.name}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: '#3a3a1a', color: '#fdcb6e', fontWeight: 600,
                        }}>
                          {d.type}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Area: <span style={{ color: '#6bcb77' }}>{d.area}</span></span>
                        <span>Density: <span style={{ color: '#ff6b6b' }}>{d.population_density}</span></span>
                        <span>ID: <span style={{ color: '#888' }}>{d.district_id}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD0D'} District Detail
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>City ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. city_xxx"
                      value={districtDetailCityId}
                      onChange={e => setDistrictDetailCityId(e.target.value)}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>District ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. district_xxx"
                      value={districtDetailDistrictId}
                      onChange={e => setDistrictDetailDistrictId(e.target.value)}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleFetchDistrictDetail}
                disabled={districtDetailLoading}
                style={districtDetailLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}
              >
                {districtDetailLoading ? 'Loading...' : '\uD83D\uDD0D Fetch District'}
              </button>

              {districtDetail && (
                <div style={{ marginTop: 10, borderLeft: '3px solid #a29bfe', paddingLeft: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 12 }}>{districtDetail.name}</span>
                    <span style={{
                      fontSize: 9, padding: '1px 6px', borderRadius: 3,
                      backgroundColor: '#1e1e1e', color: '#a29bfe', fontWeight: 600,
                    }}>
                      {districtDetail.type}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                    <span>Area: <span style={{ color: '#6bcb77' }}>{districtDetail.area}</span></span>
                    <span>Density: <span style={{ color: '#ff6b6b' }}>{districtDetail.population_density}</span></span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Buildings */}
        {activeTab === 'buildings' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#ff6b6b' }}>
                {'\uD83C\uDFE2'} Generate Buildings
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>City ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. city_xxx"
                      value={buildingsForm.city_id}
                      onChange={e => setBuildingsForm(prev => ({ ...prev, city_id: e.target.value }))}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>District ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. district_xxx"
                      value={buildingsForm.district_id}
                      onChange={e => setBuildingsForm(prev => ({ ...prev, district_id: e.target.value }))}
                    />
                  </div>
                </div>
                <div>
                  <span style={labelStyle}>Number of Buildings</span>
                  <input
                    style={darkInputStyle}
                    placeholder="10"
                    value={buildingsForm.num_buildings}
                    onChange={e => setBuildingsForm(prev => ({ ...prev, num_buildings: e.target.value }))}
                  />
                </div>
              </div>
              <button
                onClick={handleGenerateBuildings}
                disabled={buildingsLoading}
                style={buildingsLoading ? disabledBtnStyle('#ff6b6b') : primaryBtnStyle('#ff6b6b')}
              >
                {buildingsLoading ? 'Generating...' : '\uD83C\uDFE2 Generate Buildings'}
              </button>
            </div>

            {buildings && buildings.length > 0 && (
              <div style={cardStyle}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#aaa' }}>
                  Generated Buildings
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {buildings.map(b => (
                    <div key={b.building_id} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #ff6b6b',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                        <span style={{ fontWeight: 600, fontSize: 12 }}>{b.type}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: '#3a1a1a', color: '#ff6b6b', fontWeight: 600,
                        }}>
                          {b.purpose}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Height: <span style={{ color: '#fdcb6e' }}>{b.height}m</span></span>
                        <span>Area: <span style={{ color: '#6bcb77' }}>{b.area}m²</span></span>
                        <span>ID: <span style={{ color: '#888' }}>{b.building_id}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDD0D'} Buildings by District
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 10 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <div>
                    <span style={labelStyle}>City ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. city_xxx"
                      value={buildingsByDistrictCityId}
                      onChange={e => setBuildingsByDistrictCityId(e.target.value)}
                    />
                  </div>
                  <div>
                    <span style={labelStyle}>District ID *</span>
                    <input
                      style={darkInputStyle}
                      placeholder="e.g. district_xxx"
                      value={buildingsByDistrictDistrictId}
                      onChange={e => setBuildingsByDistrictDistrictId(e.target.value)}
                    />
                  </div>
                </div>
              </div>
              <button
                onClick={handleFetchBuildingsByDistrict}
                disabled={buildingsByDistrictLoading}
                style={buildingsByDistrictLoading ? disabledBtnStyle('#a29bfe') : primaryBtnStyle('#a29bfe')}
              >
                {buildingsByDistrictLoading ? 'Loading...' : '\uD83D\uDD0D Fetch Buildings'}
              </button>

              {buildingsByDistrict && buildingsByDistrict.length > 0 && (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {buildingsByDistrict.map(b => (
                    <div key={b.building_id} style={{
                      padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4,
                      border: '1px solid #2a2a3e',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10 }}>
                        <span style={{ fontWeight: 600, color: '#ff6b6b' }}>{b.type}</span>
                        <span style={{ color: '#888' }}>{b.purpose}</span>
                        <span style={{ color: '#fdcb6e' }}>{b.height}m</span>
                        <span style={{ color: '#6bcb77' }}>{b.area}m²</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Roads */}
        {activeTab === 'roads' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#a29bfe' }}>
                {'\uD83D\uDEE3\uFE0F'} Road Network
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>City ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. city_xxx"
                    value={roadsCityId}
                    onChange={e => setRoadsCityId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchRoads}
                  disabled={roadsLoading}
                  style={roadsLoading ? disabledBtnStyle('#a29bfe') : { ...primaryBtnStyle('#a29bfe'), whiteSpace: 'nowrap' }}
                >
                  {roadsLoading ? 'Loading...' : '\uD83D\uDD0D Fetch'}
                </button>
              </div>

              {roads && roads.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {roads.map(r => (
                    <div key={r.road_id} style={{
                      padding: 10, backgroundColor: '#1a1a2e', borderRadius: 6,
                      border: '1px solid #2a2a3e', borderLeft: '3px solid #a29bfe',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                        <span style={{ fontWeight: 600, fontSize: 12 }}>{r.name}</span>
                        <span style={{
                          fontSize: 9, padding: '1px 6px', borderRadius: 3,
                          backgroundColor: '#1e1e1e', color: '#a29bfe', fontWeight: 600,
                        }}>
                          {r.type}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: 8, fontSize: 9, color: '#666', flexWrap: 'wrap' }}>
                        <span>Length: <span style={{ color: '#6bcb77' }}>{r.length}m</span></span>
                        <span>Connects: <span style={{ color: '#fdcb6e' }}>{r.connects.join(', ')}</span></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Analyze */}
        {activeTab === 'analyze' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={cardStyle}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10, color: '#00d4ff' }}>
                {'\uD83D\uDCCA'} City Analysis
              </div>
              <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <span style={labelStyle}>City ID *</span>
                  <input
                    style={darkInputStyle}
                    placeholder="e.g. city_xxx"
                    value={analyzeCityId}
                    onChange={e => setAnalyzeCityId(e.target.value)}
                  />
                </div>
                <button
                  onClick={handleFetchAnalysis}
                  disabled={analyzeLoading}
                  style={analyzeLoading ? disabledBtnStyle('#00d4ff') : { ...primaryBtnStyle('#00d4ff'), whiteSpace: 'nowrap' }}
                >
                  {analyzeLoading ? 'Loading...' : '\uD83D\uDD0D Analyze'}
                </button>
              </div>

              {analysis && (
                <div style={{ borderLeft: '3px solid #00d4ff', paddingLeft: 10 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Total Area</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#00d4ff' }}>{analysis.total_area}</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Buildings</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{analysis.building_count}</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Road Network</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#fdcb6e' }}>{analysis.road_network_length}m</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Landmarks</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#ff6b6b' }}>{analysis.landmark_count}</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Density Score</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#a29bfe' }}>{(analysis.density_score * 100).toFixed(0)}%</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4 }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Walkability</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{(analysis.walkability * 100).toFixed(0)}%</span>
                    </div>
                    <div style={{ padding: 8, backgroundColor: '#1a1a2e', borderRadius: 4, gridColumn: 'span 2' }}>
                      <span style={{ fontSize: 9, color: '#888', display: 'block' }}>Green Space Ratio</span>
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#6bcb77' }}>{(analysis.green_space_ratio * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              )}
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
        <span>{'\uD83C\uDF06'} Procedural City</span>
        <span>
          {stats
            ? `${stats.total_cities ?? 0} cities · ${stats.total_districts ?? 0} districts · ${stats.total_buildings ?? 0} buildings`
            : 'Connected'}
        </span>
      </div>
    </div>
  );
}