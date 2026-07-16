"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  atlases: number;
  regions: number;
  total_utilization: number;
}

export default function TextureAtlasPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [atlasName, setAtlasName] = useState("");
  const [width, setWidth] = useState("2048");
  const [height, setHeight] = useState("2048");
  const [format, setFormat] = useState("rgba8");

  const [atlasId, setAtlasId] = useState("");
  const [algorithm, setAlgorithm] = useState("maxrects");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/texture-atlas/stats`);
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

  const handleCreateAtlas = async () => {
    if (!atlasName.trim()) {
      showMessage("Atlas name is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/texture-atlas/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: atlasName,
          width: parseInt(width, 10),
          height: parseInt(height, 10),
          format,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Texture atlas created successfully");
        setAtlasName("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create texture atlas");
    }
  };

  const handlePack = async () => {
    if (!atlasId.trim()) {
      showMessage("Atlas ID is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/texture-atlas/pack`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          atlas_id: atlasId,
          algorithm,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Texture atlas packed successfully");
        setAtlasId("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to pack texture atlas");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Texture Atlas 🗺️
      </h2>
      {message && (
        <div style={{
          background: "#1b5e20", color: "#a5d6a7", padding: "0.5rem 1rem",
          borderRadius: "0.5rem", marginBottom: "1rem", fontSize: "0.875rem"
        }}>
          {message}
        </div>
      )}
      {loading ? (
        <div style={{ color: "#888", fontSize: "0.875rem" }}>Loading...</div>
      ) : (
        <>
          <div style={{
            background: "#16213e", borderRadius: "0.75rem", padding: "1rem",
            marginBottom: "1rem", border: "1px solid #2a2a4a"
          }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>
              Statistics
            </h3>
            {stats ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "0.75rem" }}>
                {Object.entries(stats).map(([key, value]) => (
                  <div key={key} style={{
                    background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                    border: "1px solid #2a2a4a"
                  }}>
                    <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>{key}</div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                      {typeof value === "number" ? value.toLocaleString() : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: "#ff6b6b", fontSize: "0.875rem" }}>Subsystem not available</div>
            )}
          </div>

          <div style={{
            background: "#16213e", borderRadius: "0.75rem", padding: "1rem",
            marginBottom: "1rem", border: "1px solid #2a2a4a"
          }}>
            <h3 style={{ fontSize: "0.875rem", color: "#888", marginBottom: "0.75rem", textTransform: "uppercase" }}>
              Actions
            </h3>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              marginBottom: "0.75rem", border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Atlas</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Atlas Name"
                  value={atlasName}
                  onChange={(e) => setAtlasName(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="number"
                    placeholder="Width"
                    value={width}
                    onChange={(e) => setWidth(e.target.value)}
                    min="64"
                    max="8192"
                    step="64"
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <input
                    type="number"
                    placeholder="Height"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                    min="64"
                    max="8192"
                    step="64"
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <select
                    value={format}
                    onChange={(e) => setFormat(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="rgba8">RGBA8</option>
                    <option value="rgb8">RGB8</option>
                    <option value="rgba16f">RGBA16F</option>
                    <option value="bc1">BC1 (DXT1)</option>
                    <option value="bc3">BC3 (DXT5)</option>
                    <option value="bc7">BC7</option>
                  </select>
                </div>
                <button
                  onClick={handleCreateAtlas}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Create Atlas
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Pack Atlas</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="text"
                    placeholder="Atlas ID"
                    value={atlasId}
                    onChange={(e) => setAtlasId(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <select
                    value={algorithm}
                    onChange={(e) => setAlgorithm(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="maxrects">MaxRects</option>
                    <option value="guillotine">Guillotine</option>
                    <option value="shelf">Shelf</option>
                    <option value="skyline">Skyline</option>
                  </select>
                </div>
                <button
                  onClick={handlePack}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Pack
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}