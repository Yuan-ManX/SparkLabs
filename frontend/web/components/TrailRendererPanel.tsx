"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE as API_ROOT } from "../utils/api";

const API_BASE = `${API_ROOT}/agent`;

interface SubsystemStats {
  active_trails: number;
  total_points: number;
  pool_usage: number;
}

export default function TrailRendererPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [objectId, setObjectId] = useState("");
  const [configName, setConfigName] = useState("");
  const [colorStart, setColorStart] = useState("#ff4444");
  const [colorEnd, setColorEnd] = useState("#4444ff");
  const [mode, setMode] = useState("ribbon");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/trail-renderer/stats`);
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

  const handleAttach = async () => {
    if (!objectId.trim()) {
      showMessage("Object ID is required");
      return;
    }
    if (!configName.trim()) {
      showMessage("Config name is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/trail-renderer/attach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          object_id: objectId,
          config_name: configName,
          color_start: colorStart,
          color_end: colorEnd,
          mode,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Trail attached successfully");
        setObjectId("");
        setConfigName("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to attach trail");
    }
  };

  const handleClear = async () => {
    try {
      const res = await fetch(`${API_BASE}/trail-renderer/clear`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("All trails cleared");
        fetchStats();
      }
    } catch {
      showMessage("Failed to clear trails");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Trail Renderer ✨
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Attach Trail</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="text"
                    placeholder="Object ID"
                    value={objectId}
                    onChange={(e) => setObjectId(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <input
                    type="text"
                    placeholder="Config Name"
                    value={configName}
                    onChange={(e) => setConfigName(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", flex: "1" }}>
                    <span style={{ fontSize: "0.7rem", color: "#666" }}>Start</span>
                    <input
                      type="color"
                      value={colorStart}
                      onChange={(e) => setColorStart(e.target.value)}
                      style={{
                        width: "2.5rem", height: "2rem", borderRadius: "0.25rem",
                        border: "1px solid #2a2a4a", background: "#0d0d0d",
                        cursor: "pointer"
                      }}
                    />
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", flex: "1" }}>
                    <span style={{ fontSize: "0.7rem", color: "#666" }}>End</span>
                    <input
                      type="color"
                      value={colorEnd}
                      onChange={(e) => setColorEnd(e.target.value)}
                      style={{
                        width: "2.5rem", height: "2rem", borderRadius: "0.25rem",
                        border: "1px solid #2a2a4a", background: "#0d0d0d",
                        cursor: "pointer"
                      }}
                    />
                  </div>
                  <select
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d0d", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="ribbon">Ribbon</option>
                    <option value="line">Line</option>
                    <option value="dash">Dash</option>
                    <option value="particle">Particle</option>
                  </select>
                </div>
                <button
                  onClick={handleAttach}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Attach
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Clear All Trails</h4>
              <button
                onClick={handleClear}
                style={{
                  padding: "0.5rem 1rem", borderRadius: "0.375rem",
                  border: "none", background: "#e94560", color: "#fff",
                  cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                }}
              >
                Clear All
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}