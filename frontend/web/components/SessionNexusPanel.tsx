"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  total_sessions: number;
  active_sessions: number;
  total_bridges: number;
  total_checkpoints: number;
}

export default function SessionNexusPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [sessionPlatform, setSessionPlatform] = useState("web");
  const [bridgeSourceId, setBridgeSourceId] = useState("");
  const [bridgeMethod, setBridgeMethod] = useState("sync");
  const [bridgeMode, setBridgeMode] = useState("bidirectional");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/session-nexus/stats`);
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

  const handleCreateSession = async () => {
    try {
      const res = await fetch(`${API_BASE}/session-nexus/create-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform: sessionPlatform }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Session created successfully");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create session");
    }
  };

  const handleCreateBridge = async () => {
    if (!bridgeSourceId.trim()) {
      showMessage("Source ID is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/session-nexus/create-bridge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_id: bridgeSourceId,
          method: bridgeMethod,
          mode: bridgeMode,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Bridge created successfully");
        setBridgeSourceId("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to create bridge");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Session Nexus 🔗
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
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "#7c4dff" }}>
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Session</h4>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <select
                  value={sessionPlatform}
                  onChange={(e) => setSessionPlatform(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem", flex: "1 1 auto"
                  }}
                >
                  <option value="web">Web</option>
                  <option value="mobile">Mobile</option>
                  <option value="desktop">Desktop</option>
                  <option value="cli">CLI</option>
                </select>
                <button
                  onClick={handleCreateSession}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#7c4dff", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                  }}
                >
                  Create
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Create Bridge</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Source ID"
                  value={bridgeSourceId}
                  onChange={(e) => setBridgeSourceId(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <select
                    value={bridgeMethod}
                    onChange={(e) => setBridgeMethod(e.target.value)}
                    style={{
                      padding: "0.5rem", borderRadius: "0.375rem", flex: "1",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="sync">Sync</option>
                    <option value="async">Async</option>
                    <option value="stream">Stream</option>
                  </select>
                  <select
                    value={bridgeMode}
                    onChange={(e) => setBridgeMode(e.target.value)}
                    style={{
                      padding: "0.5rem", borderRadius: "0.375rem", flex: "1",
                      border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="bidirectional">Bidirectional</option>
                    <option value="unidirectional">Unidirectional</option>
                    <option value="broadcast">Broadcast</option>
                  </select>
                  <button
                    onClick={handleCreateBridge}
                    style={{
                      padding: "0.5rem 1rem", borderRadius: "0.375rem",
                      border: "none", background: "#7c4dff", color: "#fff",
                      cursor: "pointer", fontSize: "0.8rem", fontWeight: 600
                    }}
                  >
                    Create
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