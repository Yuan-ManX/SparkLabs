"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  assets_generated: number;
  pack_count: number;
  style_distribution: Record<string, number>;
}

export default function AssetSynthesizerPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [synthDescription, setSynthDescription] = useState("");
  const [synthCategory, setSynthCategory] = useState("character");
  const [synthStyle, setSynthStyle] = useState("realistic");
  const [packTheme, setPackTheme] = useState("");
  const [packCategories, setPackCategories] = useState("");
  const [packStyle, setPackStyle] = useState("realistic");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/asset-synthesizer/stats`);
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

  const handleSynthesize = async () => {
    if (!synthDescription.trim()) {
      showMessage("Description is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/asset-synthesizer/synthesize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: synthDescription,
          category: synthCategory,
          style: synthStyle,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Asset synthesized successfully");
        setSynthDescription("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to synthesize asset");
    }
  };

  const handlePack = async () => {
    if (!packTheme.trim() || !packCategories.trim()) {
      showMessage("Theme and categories are required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/asset-synthesizer/pack`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          theme: packTheme,
          categories: packCategories.split(",").map((c) => c.trim()),
          style: packStyle,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Asset pack created successfully");
        setPackTheme("");
        setPackCategories("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create asset pack");
    }
  };

  const formatStyleDistribution = (dist: Record<string, number>) => {
    return Object.entries(dist)
      .map(([k, v]) => `${k}: ${v}`)
      .join(", ");
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Asset Synthesizer 🎨
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
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Assets Generated</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                    {stats.assets_generated.toLocaleString()}
                  </div>
                </div>
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Pack Count</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#e94560" }}>
                    {stats.pack_count.toLocaleString()}
                  </div>
                </div>
                <div style={{
                  background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
                  border: "1px solid #2a2a4a"
                }}>
                  <div style={{ fontSize: "0.7rem", color: "#666", textTransform: "uppercase" }}>Style Distribution</div>
                  <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "#e94560" }}>
                    {formatStyleDistribution(stats.style_distribution)}
                  </div>
                </div>
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Synthesize Asset</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <textarea
                  placeholder="Asset description"
                  value={synthDescription}
                  onChange={(e) => setSynthDescription(e.target.value)}
                  rows={3}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem", resize: "vertical"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <select
                    value={synthCategory}
                    onChange={(e) => setSynthCategory(e.target.value)}
                    style={{
                      padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="character">Character</option>
                    <option value="environment">Environment</option>
                    <option value="prop">Prop</option>
                    <option value="ui">UI</option>
                    <option value="audio">Audio</option>
                  </select>
                  <select
                    value={synthStyle}
                    onChange={(e) => setSynthStyle(e.target.value)}
                    style={{
                      padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="realistic">Realistic</option>
                    <option value="stylized">Stylized</option>
                    <option value="pixel-art">Pixel Art</option>
                    <option value="low-poly">Low Poly</option>
                    <option value="cartoon">Cartoon</option>
                  </select>
                  <button
                    onClick={handleSynthesize}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#e94560", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Synthesize
                  </button>
                </div>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Asset Pack</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Pack theme"
                  value={packTheme}
                  onChange={(e) => setPackTheme(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <input
                  type="text"
                  placeholder="Categories (comma-separated)"
                  value={packCategories}
                  onChange={(e) => setPackCategories(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <select
                    value={packStyle}
                    onChange={(e) => setPackStyle(e.target.value)}
                    style={{
                      flex: 1, padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="realistic">Realistic</option>
                    <option value="stylized">Stylized</option>
                    <option value="pixel-art">Pixel Art</option>
                    <option value="low-poly">Low Poly</option>
                    <option value="cartoon">Cartoon</option>
                  </select>
                  <button
                    onClick={handlePack}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#e94560", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Create Pack
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}