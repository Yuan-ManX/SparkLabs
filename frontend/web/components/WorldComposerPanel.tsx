"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  blueprints: number;
  total_regions: number;
  biome_templates: number;
  [key: string]: any;
}

export default function WorldComposerPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [worldName, setWorldName] = useState("");
  const [worldDesc, setWorldDesc] = useState("");
  const [worldSize, setWorldSize] = useState("medium");

  const [biomeName, setBiomeName] = useState("");
  const [climate, setClimate] = useState("temperate");
  const [floraDensity, setFloraDensity] = useState("0.5");
  const [faunaDensity, setFaunaDensity] = useState("0.5");

  const [terrainName, setTerrainName] = useState("");
  const [gridWidth, setGridWidth] = useState("256");
  const [gridHeight, setGridHeight] = useState("256");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/world-composer/stats`);
      const data = await res.json();
      if (!data.error) setStats(data);
      else setStats(null);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const showMessage = (msg: string) => {
    setMessage(msg);
    setTimeout(() => setMessage(""), 3000);
  };

  const handleCreateWorld = async () => {
    if (!worldName.trim()) { showMessage("World name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/world-composer/create-blueprint`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: worldName, description: worldDesc, world_size: worldSize }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("World blueprint created"); setWorldName(""); fetchStats(); }
    } catch { showMessage("Failed to create world"); }
  };

  const handleCreateBiome = async () => {
    if (!biomeName.trim()) { showMessage("Biome name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/world-composer/create-biome`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: biomeName, climate, flora_density: parseFloat(floraDensity), fauna_density: parseFloat(faunaDensity) }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Biome created"); setBiomeName(""); fetchStats(); }
    } catch { showMessage("Failed to create biome"); }
  };

  const handleGenerateTerrain = async () => {
    if (!terrainName.trim()) { showMessage("Terrain name is required"); return; }
    try {
      const res = await fetch(`${API_BASE}/world-composer/generate-terrain`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: terrainName, width: parseInt(gridWidth, 10), height: parseInt(gridHeight, 10) }),
      });
      const data = await res.json();
      if (data.error) showMessage(`Error: ${data.error}`);
      else { showMessage("Terrain generated"); setTerrainName(""); fetchStats(); }
    } catch { showMessage("Failed to generate terrain"); }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        World Composer 🗺️
      </h2>
      {message && (
        <div style={{ background: "#1b5e20", color: "#a5d6a7", padding: "0.5rem 1rem", borderRadius: "0.5rem", marginBottom: "1rem", fontSize: "0.875rem" }}>{message}</div>
      )}
      {loading ? (<div style={{ color: "#888", fontSize: "0.875rem" }}>Loading...</div>) : (
        <>
          <div style={{ background: "#16213e", borderRadius: "0.75rem", padding: "1rem", marginBottom: "1rem", border: "1px solid #2a2a4a" }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>Statistics</h3>
            {stats ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.75rem" }}>
                {Object.entries(stats).map(([key, value]) => (
                  <div key={key} style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", border: "1px solid #2a2a4a" }}>
                    <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>{key}</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>{typeof value === "number" ? value.toLocaleString() : String(value)}</div>
                  </div>
                ))}
              </div>
            ) : (<div style={{ color: "#ff6b6b", fontSize: "0.875rem" }}>Subsystem not available</div>)}
          </div>

          <div style={{ background: "#16213e", borderRadius: "0.75rem", padding: "1rem", marginBottom: "1rem", border: "1px solid #2a2a4a" }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>Actions</h3>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create World Blueprint</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="World Name" value={worldName} onChange={(e) => setWorldName(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <input type="text" placeholder="Description" value={worldDesc} onChange={(e) => setWorldDesc(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <select value={worldSize} onChange={(e) => setWorldSize(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }}>
                  <option value="small">Small</option><option value="medium">Medium</option>
                  <option value="large">Large</option><option value="epic">Epic</option>
                </select>
                <button onClick={handleCreateWorld} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>
                  Create World
                </button>
              </div>
            </div>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Biome</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Biome Name" value={biomeName} onChange={(e) => setBiomeName(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <select value={climate} onChange={(e) => setClimate(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }}>
                  <option value="temperate">Temperate</option><option value="tropical">Tropical</option>
                  <option value="arid">Arid</option><option value="boreal">Boreal</option>
                  <option value="polar">Polar</option><option value="mediterranean">Mediterranean</option>
                </select>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" placeholder="Flora Density" value={floraDensity} onChange={(e) => setFloraDensity(e.target.value)} min="0" max="1" step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Fauna Density" value={faunaDensity} onChange={(e) => setFaunaDensity(e.target.value)} min="0" max="1" step="0.1"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <button onClick={handleCreateBiome} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>
                  Create Biome
                </button>
              </div>
            </div>

            <div style={{ background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem", border: "1px solid #2a2a4a" }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Generate Terrain</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input type="text" placeholder="Terrain Name" value={terrainName} onChange={(e) => setTerrainName(e.target.value)}
                  style={{ padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input type="number" placeholder="Width" value={gridWidth} onChange={(e) => setGridWidth(e.target.value)} min="32" max="4096" step="32"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                  <input type="number" placeholder="Height" value={gridHeight} onChange={(e) => setGridHeight(e.target.value)} min="32" max="4096" step="32"
                    style={{ flex: "1", padding: "0.5rem", borderRadius: "0.375rem", border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0", fontSize: "0.8rem" }} />
                </div>
                <button onClick={handleGenerateTerrain} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", background: "#e94560", color: "#fff", cursor: "pointer", fontSize: "0.8rem", fontWeight: 600, alignSelf: "flex-start" }}>
                  Generate Terrain
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}