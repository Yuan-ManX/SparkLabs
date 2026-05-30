"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/agent";

interface SubsystemStats {
  total_recordings: number;
  active_recordings: number;
  total_frames: number;
  total_size_bytes: number;
  [key: string]: any;
}

export default function DeterministicRecorderPanel() {
  const [stats, setStats] = useState<SubsystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const [recordName, setRecordName] = useState("");
  const [recordMode, setRecordMode] = useState("full");

  const [stopId, setStopId] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/deterministic-recorder/stats`);
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

  const handleStart = async () => {
    if (!recordName.trim()) {
      showMessage("Recording name is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/deterministic-recorder/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: recordName.trim(),
          mode: recordMode,
        }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Recording started successfully");
        setRecordName("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to start recording");
    }
  };

  const handleStop = async () => {
    if (!stopId.trim()) {
      showMessage("Recording ID is required");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/deterministic-recorder/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recording_id: stopId.trim() }),
      });
      const data = await res.json();
      if (data.error) {
        showMessage(`Error: ${data.error}`);
      } else {
        showMessage("Recording stopped successfully");
        setStopId("");
        fetchStats();
      }
    } catch {
      showMessage("Failed to stop recording");
    }
  };

  return (
    <div style={{ padding: "1.5rem", color: "#e0e0e0" }}>
      <h2 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "1rem", color: "#ffffff" }}>
        Deterministic Recorder 🎬
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
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Start Recording</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Recording Name"
                  value={recordName}
                  onChange={(e) => setRecordName(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <select
                  value={recordMode}
                  onChange={(e) => setRecordMode(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                >
                  <option value="full">Full Frame</option>
                  <option value="delta">Delta Only</option>
                  <option value="input_only">Input Only</option>
                  <option value="checkpoint">Checkpoint</option>
                </select>
                <button
                  onClick={handleStart}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Start Recording
                </button>
              </div>
            </div>

            <div style={{
              background: "#1a1a2e", borderRadius: "0.5rem", padding: "0.75rem",
              border: "1px solid #2a2a4a"
            }}>
              <h4 style={{ fontSize: "0.8rem", color: "#aaa", marginBottom: "0.5rem" }}>Stop Recording</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Recording ID"
                  value={stopId}
                  onChange={(e) => setStopId(e.target.value)}
                  style={{
                    padding: "0.5rem", borderRadius: "0.375rem",
                    border: "1px solid #2a2a4a", background: "#0d0d1a", color: "#e0e0e0",
                    fontSize: "0.8rem"
                  }}
                />
                <button
                  onClick={handleStop}
                  style={{
                    padding: "0.5rem 1rem", borderRadius: "0.375rem",
                    border: "none", background: "#e94560", color: "#fff",
                    cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                    alignSelf: "flex-start"
                  }}
                >
                  Stop Recording
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}