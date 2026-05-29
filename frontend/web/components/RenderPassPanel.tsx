"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  passes: number;
  enabled: number;
  executions: number;
  pipelines: number;
  [key: string]: any;
}

export default function RenderPassPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [passName, setPassName] = useState("");
  const [passType, setPassType] = useState("custom");
  const [priority, setPriority] = useState("0");
  const [enabled, setEnabled] = useState("true");

  const [pipelineName, setPipelineName] = useState("default");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/render-pass/stats`);
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

  const handleCreatePass = async () => {
    if (!passName.trim()) {
      showMessage("Pass name is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/render-pass/create-pass`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: passName,
          pass_type: passType,
          priority: parseInt(priority, 10),
          enabled: enabled === "true",
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Render pass created successfully");
        setPassName("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create render pass");
    }
  };

  const handleExecutePipeline = async () => {
    try {
      const res = await fetch(`${API_BASE}/render-pass/execute-pipeline`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pipeline_name: pipelineName }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Pipeline executed successfully");
        fetchStats();
      }
    } catch {
      showMessage("Failed to execute pipeline");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Render Pass 🎨
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Render Pass</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Pass Name"
                  value={passName}
                  onChange={(e) => setPassName(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <select
                  value={passType}
                  onChange={(e) => setPassType(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                >
                  <option value="custom">Custom</option>
                  <option value="depth_prepass">Depth Prepass</option>
                  <option value="shadow_map">Shadow Map</option>
                  <option value="opaque_geometry">Opaque Geometry</option>
                  <option value="transparent">Transparent</option>
                  <option value="post_process">Post Process</option>
                  <option value="ui_overlay">UI Overlay</option>
                </select>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <input
                    type="number"
                    placeholder="Priority"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    min="-1000"
                    max="1000"
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  />
                  <select
                    value={enabled}
                    onChange={(e) => setEnabled(e.target.value)}
                    style={{
                      flex: "1", padding: "0.5rem", borderRadius: "0.375rem",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="true">Enabled</option>
                    <option value="false">Disabled</option>
                  </select>
                </div>
                <button
                  onClick={handleCreatePass}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Create Pass
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Execute Pipeline</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Pipeline Name (default: default)"
                  value={pipelineName}
                  onChange={(e) => setPipelineName(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <button
                  onClick={handleExecutePipeline}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Execute Pipeline
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}